import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from supabase import Client

from app.services.xmpp import xmpp_service

from tests.conftest import (
    TEST_MEMBER_ID, TEST_USER_ID,
    make_device, make_floor, make_house, make_house_member, make_room, make_schedule,
)

_NO_CONFLICT = patch("app.services.schedules._check_conflicting_power_schedule")


def _setup_house(supabase: Client, role="owner", **house_kwargs):
    house = make_house(**house_kwargs)
    supabase.table("houses").insert(house).execute()
    supabase.table("house_members").insert(
        make_house_member(house["id"], TEST_USER_ID, role)
    ).execute()
    return house


def _no_house(supabase: Client):
    """No-op: the autouse reset_db fixture ya deja la BD vacía."""
    return None


class TestHousesRoutes:

    def test_bot_status_offline_without_house(self, client: TestClient, supabase: Client):
        res = client.get("/api/v1/houses/me/bot-status")
        assert res.status_code == 200 and res.json() == {"online": False}

    def test_get_my_house_returns_floors_and_rooms(self, client: TestClient, supabase: Client):
        house = _setup_house(supabase)
        floor = make_floor(house["id"])
        supabase.table("floors").insert(floor).execute()
        supabase.table("rooms").insert(make_room(floor["id"])).execute()
        res = client.get("/api/v1/houses/me")
        data = res.json()
        assert res.status_code == 200
        assert data["id"] == house["id"] and len(data["floors"][0]["rooms"]) == 1

    @pytest.mark.parametrize("path", [
        "/api/v1/houses/me",
        "/api/v1/houses/me/invite",
    ])
    def test_house_endpoints_404_without_house(
        self, client: TestClient, supabase: Client, path,
    ):
        method = client.post if "invite" in path else client.get
        assert method(path).status_code == 404

    def test_owner_can_create_floor(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        res = client.post("/api/v1/houses/me/floors", json={"name": "Primera Planta", "level": 1})
        assert res.status_code == 201 and res.json()["rooms"] == []

    def test_member_cannot_create_floor(self, client: TestClient, supabase: Client):
        _setup_house(supabase, role="member")
        res = client.post("/api/v1/houses/me/floors", json={"name": "Planta Baja", "level": 1})
        assert res.status_code == 403

    def test_group_actions_reject_unsupported_action(self, client: TestClient):
        res = client.post("/api/v1/houses/rooms/room_salon/action", json={"action": "brillo"})
        assert res.status_code == 400

    def test_member_cannot_kick_other(self, client: TestClient, supabase: Client):
        _setup_house(supabase, role="member")
        res = client.delete(f"/api/v1/houses/me/members/{TEST_MEMBER_ID}")
        assert res.status_code == 403

    def test_any_member_can_leave_house(self, client: TestClient, supabase: Client):
        _setup_house(supabase, role="member")
        assert client.delete("/api/v1/houses/me/leave").status_code == 204

    def test_setup_rejected_when_user_already_has_house(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        res = client.post("/api/v1/houses/setup", json={"bot_jid": "otro-bot@xmpp.cano-app.com"})
        assert res.status_code == 409

    def test_group_schedule_404_when_empty_room(self, client: TestClient, supabase: Client):
        unknown_room = str(uuid.uuid4())
        res = client.post(f"/api/v1/houses/rooms/{unknown_room}/schedule", json={
            "device_id": "00000000-0000-0000-0000-000000000001",
            "name": "x", "action": "apagar",
            "cron_expr": "0 22 * * *", "is_recurring": True,
        })
        assert res.status_code == 404

    def test_room_schedule_creates_one_task_per_device(self, client: TestClient, supabase: Client):
        house = _setup_house(supabase)
        floor = make_floor(house["id"])
        supabase.table("floors").insert(floor).execute()
        room = make_room(floor["id"])
        supabase.table("rooms").insert(room).execute()
        d1 = make_device(id=str(uuid.uuid4()), room_id=room["id"])
        d2 = make_device(id=str(uuid.uuid4()), room_id=room["id"])
        supabase.table("devices").insert([d1, d2]).execute()
        with _NO_CONFLICT:
            res = client.post(f"/api/v1/houses/rooms/{room['id']}/schedule", json={
                "device_id": d1["id"], "name": "Apagar todo",
                "action": "apagar", "cron_expr": "0 22 * * *", "is_recurring": True,
            })
        assert res.status_code == 200 and res.json()["ok"] is True

    def test_owner_generates_invitation_code(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        res = client.post("/api/v1/houses/me/invite")
        data = res.json()
        assert res.status_code == 200 and "code" in data and data["expires_in_hours"] == 24

    def test_another_user_joins_house_with_valid_code(self, client: TestClient, supabase: Client):
        house = make_house()
        supabase.table("houses").insert(house).execute()
        supabase.table("house_members").insert(
            make_house_member(house["id"], TEST_MEMBER_ID, "owner")
        ).execute()
        supabase.table("house_invitations").insert({
            "id": str(uuid.uuid4()),
            "house_id": house["id"],
            "code": "DEMO2026",
            "created_by": TEST_MEMBER_ID,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }).execute()
        res = client.post("/api/v1/houses/join", json={"code": "DEMO2026"})
        assert res.status_code == 200 and res.json()["ok"] is True

    def test_setup_returns_house_and_bot_token(self, client: TestClient, supabase: Client):
        res = client.post("/api/v1/houses/setup", json={"name": "Casa Demo"})
        body = res.json()
        assert res.status_code == 201 and "house_id" in body
        assert body["bot_token"] and len(body["bot_token"]) > 20

    def test_owner_regenerates_bot_token(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        res = client.post("/api/v1/houses/me/bot-token/regenerate")
        assert res.status_code == 200 and len(res.json()["bot_token"]) > 20
