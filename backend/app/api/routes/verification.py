import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.db import supabase
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])

CODE_EXPIRY_MINUTES = 15


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


@router.get("/resolve-username/{username}")
def resolve_username(username: str):
    """Returns the email associated with a username (used for login)."""
    row = supabase.table("base_user").select("email").eq("username", username.lower()).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"email": row.data[0]["email"]}


class SendVerificationRequest(BaseModel):
    email: EmailStr
    first_name: str | None = None


@router.post("/send-verification", status_code=200)
def send_verification(body: SendVerificationRequest):
    email = body.email.lower().strip()

    # Check email not already registered
    existing = supabase.table("base_user").select("id").eq("email", email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Este correo ya está registrado")

    # Invalidate any previous unused codes for this email
    supabase.table("email_verifications").update({"used": True})\
        .eq("email", email).eq("used", False).execute()

    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)

    supabase.table("email_verifications").insert({
        "email":      email,
        "code":       code,
        "expires_at": expires_at.isoformat(),
        "used":       False,
    }).execute()

    send_verification_email(to_email=email, first_name=body.first_name, code=code)

    return {"ok": True, "message": f"Código enviado a {email}"}


def validate_verification_code(email: str, code: str) -> None:
    """Raises HTTPException if the code is invalid, expired or already used."""
    email = email.lower().strip()
    now = datetime.now(timezone.utc).isoformat()

    row = supabase.table("email_verifications")\
        .select("id, used, expires_at")\
        .eq("email", email)\
        .eq("code", code)\
        .eq("used", False)\
        .gt("expires_at", now)\
        .order("expires_at", desc=True)\
        .limit(1)\
        .execute()

    if not row.data:
        raise HTTPException(status_code=400, detail="Código inválido o expirado")

    supabase.table("email_verifications")\
        .update({"used": True})\
        .eq("id", row.data[0]["id"])\
        .execute()
