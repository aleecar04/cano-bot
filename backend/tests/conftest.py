"""
Configuración de tests para el backend FastAPI.
Estrategia: mock completo del cliente Supabase + override de get_current_user.

IMPORTANTE: el supabase_mock se inyecta en app.core.db ANTES de cualquier import
de los módulos de la app. Si lo hiciéramos dentro de un fixture, los módulos
ya importados al colectar tests tendrían una referencia al supabase real,
causando contaminación entre tests de services y tests de routes.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


# ── Supabase builder mock ─────────────────────────────────────────────────────

class _QueryBuilder:
    """Mock del patrón builder de Supabase: table().select().eq().execute()"""

    def __init__(self, return_data: list[dict] | None = None):
        self._data = return_data if return_data is not None else []
        self._inserted: list[dict] | None = None

    def select(self, *a, **kw) -> "_QueryBuilder": return self
    def insert(self, data=None, *a, **kw) -> "_QueryBuilder":
        if isinstance(data, dict):
            self._inserted = [{**data, "id": self._data[0]["id"] if self._data else str(uuid.uuid4())}]
        return self
    def update(self, *a, **kw) -> "_QueryBuilder": return self
    def delete(self, *a, **kw) -> "_QueryBuilder": return self
    def upsert(self, *a, **kw) -> "_QueryBuilder": return self
    def eq(self, *a, **kw) -> "_QueryBuilder": return self
    def neq(self, *a, **kw) -> "_QueryBuilder": return self
    def in_(self, *a, **kw) -> "_QueryBuilder": return self
    def is_(self, *a, **kw) -> "_QueryBuilder": return self
    def lte(self, *a, **kw) -> "_QueryBuilder": return self
    def gte(self, *a, **kw) -> "_QueryBuilder": return self
    def order(self, *a, **kw) -> "_QueryBuilder": return self
    def limit(self, *a, **kw) -> "_QueryBuilder": return self
    def single(self, *a, **kw) -> "_QueryBuilder": return self

    def execute(self) -> MagicMock:
        result = MagicMock()
        result.data = self._inserted if self._inserted is not None else self._data
        return result


class SupabaseMock:
    """
    Mock del cliente Supabase con respuestas configurables por tabla.

    Uso dentro de un test:
        supabase_mock.set_data("houses", [{"id": "...", ...}])
    """

    def __init__(self):
        self._table_data: dict[str, list[dict]] = {}

    def set_data(self, table: str, data: list[dict]) -> None:
        self._table_data[table] = data

    def clear(self) -> None:
        self._table_data = {}

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self._table_data.get(name, []))

    auth = MagicMock()


# ── Constantes de test ────────────────────────────────────────────────────────

TEST_USER_ID   = str(uuid.uuid4())
TEST_USER = {
    "id": TEST_USER_ID,
    "email": "test@example.com",
    "username": "testuser",
    "is_active": True,
    "is_superuser": False,
}
TEST_HOUSE_ID  = str(uuid.uuid4())
TEST_HOUSE     = {"id": TEST_HOUSE_ID, "user_id": TEST_USER_ID, "name": "Mi Casa"}
TEST_MEMBER_ID = str(uuid.uuid4())  # second user in same house

WEBHOOK_SECRET = "test-webhook-secret"


# ── Inyección de supabase_mock antes de cualquier import de la app ───────────

_SUPABASE_MOCK = SupabaseMock()
import app.core.db  # noqa: E402
app.core.db.supabase = _SUPABASE_MOCK


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def supabase_mock() -> SupabaseMock:
    return _SUPABASE_MOCK


@pytest.fixture(scope="session")
def client(supabase_mock: SupabaseMock) -> TestClient:
    """TestClient con autenticación anulada. bot_auth se sobreescribe para
    devolver la house de test, así los endpoints con bot_token funcionan
    sin necesidad de header."""
    from app.main import app
    from app.api.deps import get_current_user
    from app.api.bot_auth import bot_auth

    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[bot_auth] = lambda: {"id": TEST_HOUSE_ID}

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_supabase(supabase_mock: SupabaseMock):
    supabase_mock.clear()
    yield
    supabase_mock.clear()


# ── Helpers de datos ──────────────────────────────────────────────────────────

def make_house(**kwargs) -> dict:
    return {
        "id": TEST_HOUSE_ID,
        "user_id": TEST_USER_ID,
        "name": "Mi Casa",
        "bot_token_hash": "a" * 64,  # sha256 hex de prueba
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
        "name": "Luz salón",
        "type": "Luz",
        "driver": "tuya",
        "ip": "192.168.1.100",
        "mac": "AA:BB:CC:DD:EE:FF",
        "config": {},
        "estado": {},
        "is_online": True,
        "room_id": None,
        "location": None,
        "last_seen_at": None,
        "registered_at": None,
        "updated_at": None,
        **kwargs,
    }


def make_floor(house_id: str, **kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "house_id": house_id,
        "name": "Planta Baja",
        "level": 0,
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
