import secrets
from app.core.config import settings
from app.core.db import supabase
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.models.users import UserCreate, UserUpdate, UserUpdateMe, UserRegister
from app.services.xmpp import create_xmpp_account
from app.repositories.users import user_repository, xmpp_account_repository
from app.repositories.houses import house_member_repository


# ── Read helpers ─────────────────────────────────────────────────────────────
def get_user_by_email(email: str) -> dict | None:
    return user_repository.find_by_email(email)


def list_users(skip: int = 0, limit: int = 100) -> dict:
    """Paginated list of users with total count."""
    return user_repository.find_paginated(skip, limit)


def resolve_jid_in_house(jid: str, house_id: str) -> str | None:
    """Resuelve un JID (bare) a user_id SOLO si ese usuario pertenece a la casa dada.
    Devuelve None si el JID no existe o el usuario no es miembro de esa casa.
    Es el control de acceso del bot: solo procesa comandos de miembros de su casa."""
    user_id = xmpp_account_repository.find_user_id_by_jid(jid)
    if not user_id:
        return None
    if house_member_repository.find_house_id_by_user(user_id) != house_id:
        return None
    return user_id


def resolve_username_to_email(username: str) -> str:
    """Return the email associated with a username (login flow).
    Raises UserNotFound if the username is unknown."""
    email = user_repository.find_email_by_username(username)
    if not email:
        raise not_found("Usuario no encontrado")
    return email


def get_user_by_id(user_id: str, current_user: dict) -> dict:
    """Get user info. Non-superusers can only see themselves.
    Raises UserNotFound / UserPermissionDenied."""
    user = user_repository.find_by_id(user_id)
    if not user:
        raise not_found("User not found")
    if user["id"] != current_user["id"] and not current_user.get("is_superuser"):
        raise forbidden("The user doesn't have enough privileges")
    return user


# ── Creation flows ──────────────────────────────────────────────────────────
async def create_user_with_xmpp(
    email: str,
    password: str,
    username: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    """Create a user in Supabase Auth + base_user + XMPP account.
    Si algún paso posterior al Auth falla, deshace lo creado en nuestra BD
    (Supabase Auth + base_user). La cuenta XMPP en Prosody se gestiona aparte."""
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id

    try:
        xmpp_password = await create_xmpp_account(username=username)
        jid = f"{username}@{settings.XMPP_DOMAIN}"

        supabase.table("base_user").insert({
            "id": user_id,
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }).execute()

        supabase.rpc("insert_xmpp_account", {
            "p_user_id": user_id,
            "p_jid": jid,
            "p_password": xmpp_password,
            "p_key": settings.XMPP_ENCRYPTION_KEY,
        }).execute()
    except Exception:
        # Rollback BD: borramos lo nuestro para no dejar usuario zombi.
        try:
            supabase.table("base_user").delete().eq("id", user_id).execute()
        except Exception:
            pass
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception:
            pass
        raise

    return user_repository.find_by_id(user_id)


def create_user_simple(email: str, password: str, username: str | None = None) -> dict:
    """Create a user without a real XMPP account (testing/admin)."""
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id
    username = username or email.split("@")[0]
    jid = f"{username}@{settings.XMPP_DOMAIN}"
    dummy_password = secrets.token_urlsafe(16)

    supabase.table("base_user").insert({
        "id": user_id,
        "username": username,
        "email": email,
        "first_name": None,
        "last_name": None,
    }).execute()

    supabase.rpc("insert_xmpp_account", {
        "p_user_id": user_id,
        "p_jid": jid,
        "p_password": dummy_password,
        "p_key": settings.XMPP_ENCRYPTION_KEY,
    }).execute()

    return user_repository.find_by_id(user_id)


def create_user_for_admin(user_in: UserCreate) -> dict:
    """Admin creation flow. Raises EmailAlreadyExists (400) if email is taken."""
    if get_user_by_email(email=user_in.email):
        raise bad_request("The user with this email already exists in the system.")
    return create_user_simple(email=user_in.email, password=user_in.password)


async def register(user_in: UserRegister) -> dict:
    """Public signup: check username + create user.
    Raises UsernameAlreadyTaken."""
    if user_repository.exists_by_username(user_in.username):
        raise bad_request("Username already taken")
    return await create_user_with_xmpp(
        email=user_in.email,
        password=user_in.password,
        username=user_in.username,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )


# ── Profile / me ─────────────────────────────────────────────────────────────
def get_profile(current_user: dict) -> dict:
    """Compose the full user profile for /me/profile."""
    user_id = current_user["id"]

    row = user_repository.find_basic_by_id(user_id) or {}
    jid = xmpp_account_repository.find_jid_by_user(user_id)

    first = row.get("first_name") or ""
    last = row.get("last_name") or ""
    full = f"{first} {last}".strip() or None

    return {
        "id":            current_user["id"],
        "email":         current_user.get("email"),
        "is_active":     current_user.get("is_active"),
        "is_superuser": current_user.get("is_superuser"),
        "full_name":    full,
        "created_at":   current_user.get("created_at"),
        "username":     row.get("username"),
        "first_name":   row.get("first_name"),
        "last_name":    row.get("last_name"),
        "xmpp_jid":     jid,
    }


def update_me(user_id: str, user_in: UserUpdateMe) -> dict:
    """Update own profile. Raises EmailConflict (409) if email is taken by another user."""
    if user_in.email:
        existing = get_user_by_email(email=user_in.email)
        if existing and existing["id"] != user_id:
            raise conflict("User with this email already exists")
    data = user_in.model_dump(exclude_unset=True)
    result = supabase.table("base_user").update(data).eq("id", user_id).execute()
    return result.data[0]


def change_password_me(email: str, current_password: str, new_password: str) -> None:
    """Verify current password against Supabase Auth, then update.
    Raises SamePasswordError / InvalidCurrentPassword / PasswordUpdateFailed."""
    if current_password == new_password:
        raise bad_request("New password cannot be the same as the current one")
    try:
        supabase.auth.sign_in_with_password({
            "email":    email,
            "password": current_password,
        })
    except Exception:
        raise bad_request("Incorrect current password")
    try:
        supabase.auth.update_user({"password": new_password})
    except Exception:
        raise bad_request("Could not update password")


def delete_me(current_user: dict) -> None:
    """Delete own account. Raises SuperuserCannotDelete."""
    if current_user.get("is_superuser"):
        raise forbidden("Super users are not allowed to delete themselves")
    supabase.table("base_user").delete().eq("id", current_user["id"]).execute()


# ── Admin flows ─────────────────────────────────────────────────────────────
def admin_update_user(user_id: str, user_in: UserUpdate) -> dict:
    """Admin updates any user. Raises UserNotFound / EmailConflict."""
    if not user_repository.find_by_id(user_id):
        raise not_found("The user with this id does not exist in the system")
    if user_in.email:
        owner = get_user_by_email(email=user_in.email)
        if owner and owner["id"] != user_id:
            raise conflict("User with this email already exists")
    data = user_in.model_dump(exclude_unset=True)
    data.pop("password", None)
    result = supabase.table("base_user").update(data).eq("id", user_id).execute()
    return result.data[0]


def admin_delete_user(user_id: str, current_user: dict) -> None:
    """Admin deletes a user (cannot delete self).
    Raises UserNotFound / SuperuserCannotDelete."""
    user = user_repository.find_by_id(user_id)
    if not user:
        raise not_found("User not found")
    if user["id"] == current_user["id"]:
        raise forbidden("Super users are not allowed to delete themselves")
    supabase.table("base_user").delete().eq("id", user_id).execute()
