from __future__ import annotations

import json
import os
import subprocess
import uuid


def _supabase_status() -> dict:
    out = subprocess.check_output(
        ["supabase", "status", "--output", "json"],
        stderr=subprocess.DEVNULL,
    )
    raw = json.loads(out)
    return {
        "url": raw.get("API_URL") or raw.get("api_url") or "http://localhost:54321",
        "key": raw.get("SERVICE_ROLE_KEY") or raw.get("service_role_key"),
    }


_SUPA = _supabase_status()

os.environ["PROJECT_NAME"] = "test"
os.environ["SUPABASE_URL"] = _SUPA["url"]
os.environ["SUPABASE_KEY"] = _SUPA["key"]
os.environ.setdefault("XMPP_BOT_JID", "bot@test")
os.environ.setdefault("XMPP_ADMIN_USER", "admin@test")
os.environ.setdefault("XMPP_ADMIN_PASSWORD", "test123")
os.environ.setdefault("XMPP_REST_URL", "http://test/rest")
os.environ.setdefault("XMPP_ENCRYPTION_KEY", "0" * 64)

import pytest
from fastapi.testclient import TestClient
from supabase import create_client, Client


TEST_USER_ID   = str(uuid.uuid4())
TEST_USER = {
    "id": TEST_USER_ID,
    "email": "test@example.com",
    "username": "testuser",
    "is_active": True,
}
TEST_HOUSE_ID  = str(uuid.uuid4())
TEST_HOUSE     = {"id": TEST_HOUSE_ID, "user_id": TEST_USER_ID, "name": "Mi Casa"}
TEST_MEMBER_ID = str(uuid.uuid4())

WEBHOOK_SECRET = "test-webhook-secret"


_TABLES_TO_RESET = [
    "favorite_actions",
    "schedules",
    "commands",
    "messages",
    "conversations",
    "devices",
    "ha_integrations",
    "rooms",
    "floors",
    "house_invitations",
    "house_members",
    "houses",
]


_REAL_SUPABASE: Client = create_client(_SUPA["url"], _SUPA["key"])


@pytest.fixture(scope="session")
def supabase() -> Client:
    return _REAL_SUPABASE


import app.core.db  # noqa: E402
app.core.db.supabase = _REAL_SUPABASE


@pytest.fixture(scope="session", autouse=True)
def _setup_auth_users():
    for user_id, email, username in [
        (TEST_USER_ID, "test@example.com", "testuser"),
        (TEST_MEMBER_ID, "member@example.com", "memberuser"),
    ]:
        try:
            _REAL_SUPABASE.auth.admin.create_user({
                "id": user_id,
                "email": email,
                "password": "testpass123",
                "email_confirm": True,
            })
        except Exception:
            pass
        try:
            _REAL_SUPABASE.table("base_user").upsert({
                "id": user_id,
                "username": username,
                "email": email,
                "is_active": True,
            }).execute()
        except Exception:
            pass
    yield
    for user_id in (TEST_USER_ID, TEST_MEMBER_ID):
        try:
            _REAL_SUPABASE.auth.admin.delete_user(user_id)
        except Exception:
            pass


def _truncate_all() -> None:
    sentinel = "00000000-0000-0000-0000-000000000000"
    for table in _TABLES_TO_RESET:
        try:
            _REAL_SUPABASE.table(table).delete().neq("id", sentinel).execute()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def reset_db():
    _truncate_all()
    yield
    _truncate_all()


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app
    from app.api.deps import get_current_user
    from app.api.bot_auth import bot_auth

    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[bot_auth] = lambda: {"id": TEST_HOUSE_ID}

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def make_house(**kwargs) -> dict:
    return {
        "id": TEST_HOUSE_ID,
        "name": "Mi Casa",
        "bot_token_hash": "a" * 64,
        **kwargs,
    }


def make_house_member(house_id: str = TEST_HOUSE_ID, user_id: str = TEST_USER_ID, role: str = "owner") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "house_id": house_id,
        "user_id": user_id,
        "role": role,
        "created_at": "2026-04-16T10:00:00+00:00",
    }


def make_device(**kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "owner_id": TEST_USER_ID,
        "house_id": TEST_HOUSE_ID,
        "name": f"Luz {uuid.uuid4().hex[:6]}",
        "type": "Luz",
        "driver": "tuya",
        "ip": "192.168.1.100",
        "mac": f"AA:BB:CC:{uuid.uuid4().hex[:2]}:{uuid.uuid4().hex[:2]}:{uuid.uuid4().hex[:2]}".upper(),
        "config": {},
        "state": {},
        "is_online": True,
        "room_id": None,
        **kwargs,
    }


def make_floor(house_id: str, **kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "house_id": house_id,
        "name": "Planta Baja",
        **kwargs,
    }


def make_room(floor_id: str, **kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "floor_id": floor_id,
        "name": "Salón",
        **kwargs,
    }


def make_schedule(**kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": TEST_USER_ID,
        "device_id": str(uuid.uuid4()),
        "name": "Apagar luces",
        "action": "apagar",
        "payload": {},
        "cron_expr": "0 22 * * *",
        "next_run_at": "2026-04-17T22:00:00+00:00",
        "is_active": True,
        "last_command_id": None,
        "created_at": "2026-04-16T10:00:00+00:00",
        "updated_at": "2026-04-16T10:00:00+00:00",
        **kwargs,
    }


def make_favorite(**kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": TEST_USER_ID,
        "device_id": str(uuid.uuid4()),
        "action": "encender",
        "payload": {},
        "label": "Encender luz salón",
        "created_at": "2026-04-16T10:00:00+00:00",
        **kwargs,
    }
