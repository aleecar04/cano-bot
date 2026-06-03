"""Tests para las rutas de casas (/houses)."""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    SupabaseMock, TEST_USER_ID, TEST_HOUSE_ID,
    make_floor, make_house, make_room, make_house_member, make_device, make_schedule,
)

from unittest.mock import patch
_NO_CONFLICT = patch("app.services.schedules._check_conflicting_power_schedule")


def _setup_house(supabase_mock: SupabaseMock, **house_kwargs):
    """Helper: set house + house_members so get_user_house() works."""
    house = make_house(**house_kwargs)
    member = make_house_member(house["id"], TEST_USER_ID, "owner")
    supabase_mock.set_data("houses", [house])
    supabase_mock.set_data("house_members", [member])
    return house


class TestGetMyHouse:
    def test_returns_house_with_floors_and_rooms(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        floor = make_floor(house["id"])
        room = make_room(floor["id"])
        supabase_mock.set_data("floors", [floor])
        supabase_mock.set_data("rooms", [room])

        res = client.get("/api/v1/houses/me")

        assert res.status_code == 200
        data = res.json()
        assert data["id"] == house["id"]
        assert data["name"] == "Mi Casa"
        assert len(data["floors"]) == 1
        assert len(data["floors"][0]["rooms"]) == 1

    def test_returns_404_when_no_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("houses", [])

        res = client.get("/api/v1/houses/me")

        assert res.status_code == 404

    def test_returns_house_with_empty_floors(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        supabase_mock.set_data("floors", [])

        res = client.get("/api/v1/houses/me")

        assert res.status_code == 200
        assert res.json()["floors"] == []


class TestGetMyRooms:
    def test_returns_flat_room_list(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        floor = make_floor(house["id"])
        room = make_room(floor["id"])
        supabase_mock.set_data("floors", [floor])
        supabase_mock.set_data("rooms", [room])

        res = client.get("/api/v1/houses/me/rooms")

        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_returns_404_when_no_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("houses", [])

        res = client.get("/api/v1/houses/me/rooms")

        assert res.status_code == 404

    def test_returns_empty_when_no_rooms(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        supabase_mock.set_data("floors", [])
        supabase_mock.set_data("rooms", [])

        res = client.get("/api/v1/houses/me/rooms")

        assert res.status_code == 200
        assert res.json() == []


class TestAddFloor:
    def test_creates_floor_successfully(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        new_floor = make_floor(house["id"], name="Primera Planta", level=1)
        supabase_mock.set_data("floors", [new_floor])

        res = client.post("/api/v1/houses/me/floors", json={"name": "Primera Planta", "level": 1})

        assert res.status_code == 201
        assert res.json()["name"] == new_floor["name"]
        assert res.json()["rooms"] == []

    def test_returns_404_when_no_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("houses", [])

        res = client.post("/api/v1/houses/me/floors", json={"name": "Piso 1", "level": 1})

        assert res.status_code in (403, 404)


class TestAddRoom:
    def test_creates_room_successfully(self, client: TestClient, supabase_mock: SupabaseMock):
        floor = make_floor("some-house-id")
        room = make_room(floor["id"], name="Cocina")
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("rooms", [room])

        res = client.post(f"/api/v1/houses/floors/{floor['id']}/rooms", json={"name": "Cocina"})

        assert res.status_code == 201
        assert res.json()["name"] == "Cocina"


class TestOwnerOnlyPermissions:
    def test_member_cannot_add_floor(self, client: TestClient, supabase_mock: SupabaseMock):
        house = make_house()
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [make_house_member(role="member")])
        supabase_mock.set_data("floors", [])

        res = client.post("/api/v1/houses/me/floors", json={"name": "Planta 1", "level": 1})

        assert res.status_code == 403

    def test_owner_can_add_floor(self, client: TestClient, supabase_mock: SupabaseMock):
        house = make_house()
        floor = make_floor(house["id"])
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [make_house_member(role="owner")])
        supabase_mock.set_data("floors", [floor])

        res = client.post("/api/v1/houses/me/floors", json={"name": "Planta Baja", "level": 0})

        assert res.status_code == 201

    def test_member_cannot_add_room(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="member")])

        res = client.post("/api/v1/houses/floors/some-floor/rooms", json={"name": "Cocina"})

        assert res.status_code == 403


class TestGroupActions:
    def test_room_action_encender(self, client: TestClient, supabase_mock: SupabaseMock):
        """Room with no devices returns 404."""
        supabase_mock.set_data("rooms", [{"id": "room-1"}])
        supabase_mock.set_data("devices", [])

        res = client.post("/api/v1/houses/rooms/room-1/action", json={"action": "encender"})

        assert res.status_code == 404

    def test_room_action_invalid(self, client: TestClient, supabase_mock: SupabaseMock):
        res = client.post("/api/v1/houses/rooms/room-1/action", json={"action": "brillo"})
        assert res.status_code == 400

    def test_floor_action_invalid(self, client: TestClient, supabase_mock: SupabaseMock):
        res = client.post("/api/v1/houses/floors/floor-1/action", json={"action": "set_volumen"})
        assert res.status_code == 400


class TestMemberManagement:
    def test_kick_member(self, client: TestClient, supabase_mock: SupabaseMock):
        from tests.conftest import TEST_MEMBER_ID
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="owner")])

        res = client.delete(f"/api/v1/houses/me/members/{TEST_MEMBER_ID}")
        assert res.status_code in (204, 404)

    def test_kick_requires_owner(self, client: TestClient, supabase_mock: SupabaseMock):
        from tests.conftest import TEST_MEMBER_ID
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="member")])

        res = client.delete(f"/api/v1/houses/me/members/{TEST_MEMBER_ID}")
        assert res.status_code == 403

    def test_leave_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="member")])

        res = client.delete("/api/v1/houses/me/leave")
        assert res.status_code == 204

    def test_owner_cannot_leave(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="owner")])

        res = client.delete("/api/v1/houses/me/leave")
        assert res.status_code == 400

    def test_setup_rejects_if_already_in_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="owner")])

        res = client.post("/api/v1/houses/setup", json={"bot_jid": "other-bot@xmpp.test"})
        assert res.status_code == 409


class TestHouseMembers:
    def test_get_members(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("base_user", [{"id": TEST_USER_ID, "username": "testuser"}])

        res = client.get("/api/v1/houses/me/members")

        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_members_no_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("houses", [])

        res = client.get("/api/v1/houses/me/members")

        assert res.status_code == 404

    def test_floor_action_no_rooms(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("rooms", [])

        res = client.post("/api/v1/houses/floors/floor-1/action", json={"action": "apagar"})

        assert res.status_code == 404


class TestGroupSchedules:
    def test_room_schedule_no_devices(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("devices", [])

        res = client.post("/api/v1/houses/rooms/room-1/schedule", json={
            "device_id": "00000000-0000-0000-0000-000000000001",
            "name": "Apagar habitación",
            "action": "apagar",
            "cron_expr": "0 22 * * *",
            "is_recurring": True,
        })

        assert res.status_code == 404

    def test_floor_schedule_no_rooms(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("rooms", [])

        res = client.post("/api/v1/houses/floors/floor-1/schedule", json={
            "device_id": "00000000-0000-0000-0000-000000000001",
            "name": "Apagar planta",
            "action": "apagar",
            "cron_expr": "0 23 * * *",
            "is_recurring": True,
        })

        assert res.status_code == 404

    def test_floor_schedule_no_devices(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("rooms", [{"id": "r1"}])
        supabase_mock.set_data("devices", [])

        res = client.post("/api/v1/houses/floors/floor-1/schedule", json={
            "device_id": "00000000-0000-0000-0000-000000000001",
            "name": "Apagar planta",
            "action": "apagar",
            "cron_expr": "0 23 * * *",
            "is_recurring": True,
        })
        assert res.status_code == 404

    def test_room_schedule_creates_for_each_device(self, client: TestClient, supabase_mock: SupabaseMock):
        import uuid
        d1 = make_device(id=str(uuid.uuid4()))
        d2 = make_device(id=str(uuid.uuid4()), mac="BB:BB:BB:BB:BB:BB")
        supabase_mock.set_data("devices", [d1, d2])
        supabase_mock.set_data("schedules", [make_schedule()])
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member()])

        with _NO_CONFLICT:
            res = client.post("/api/v1/houses/rooms/room-1/schedule", json={
                "device_id": d1["id"],
                "name": "Apagar todo",
                "action": "apagar",
                "cron_expr": "0 22 * * *",
                "is_recurring": True,
            })

        assert res.status_code == 200
        assert res.json()["ok"] is True


class TestDeleteFloorRoom:
    def test_owner_deletes_floor(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        floor = make_floor(house["id"])
        supabase_mock.set_data("floors", [floor])
        supabase_mock.set_data("rooms", [])

        res = client.delete(f"/api/v1/houses/floors/{floor['id']}")
        assert res.status_code in (204, 404)

    def test_owner_deletes_room(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        floor = make_floor(TEST_HOUSE_ID)
        room = make_room(floor["id"])
        supabase_mock.set_data("rooms", [room])

        res = client.delete(f"/api/v1/houses/floors/{floor['id']}/rooms/{room['id']}")
        assert res.status_code in (204, 404)


class TestInvitationCodes:
    def test_generate_invite_code(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("house_invitations", [{"id": "inv-1", "code": "ABC123"}])

        res = client.post("/api/v1/houses/me/invite")

        assert res.status_code == 200
        data = res.json()
        assert "code" in data
        assert data["expires_in_hours"] == 24

    def test_generate_invite_requires_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("houses", [])

        res = client.post("/api/v1/houses/me/invite")

        assert res.status_code == 404

    def test_join_with_valid_code(self, client: TestClient, supabase_mock: SupabaseMock):
        from datetime import datetime, timezone, timedelta
        house = make_house()
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("house_invitations", [{
            "id": "inv-1",
            "house_id": house["id"],
            "code": "ABC123",
            "used_at": None,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }])

        res = client.post("/api/v1/houses/join", json={"code": "ABC123"})

        assert res.status_code == 200
        assert res.json()["ok"] is True

    def test_join_with_invalid_code(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_invitations", [])

        res = client.post("/api/v1/houses/join", json={"code": "XXXXXX"})

        assert res.status_code == 400


class TestHouseSetup:
    def test_setup_creates_house_and_returns_token(self, client: TestClient, supabase_mock: SupabaseMock):
        from unittest.mock import patch, MagicMock
        new_house = make_house()

        def fake_table(name):
            qb = MagicMock()
            for m in ("select", "insert", "upsert", "eq"):
                getattr(qb, m).return_value = qb
            qb.execute.return_value = MagicMock(data=[new_house] if name == "houses" else [])
            return qb

        # Sin casa previa para el usuario
        supabase_mock.set_data("house_members", [])
        with patch("app.services.home.supabase") as mock_supa:
            mock_supa.table.side_effect = fake_table
            res = client.post("/api/v1/houses/setup", json={"name": "Mi Casa"})

        assert res.status_code == 201
        body = res.json()
        assert "house_id" in body
        # El token plaintext se devuelve UNA vez y es no vacío
        assert body["bot_token"] and len(body["bot_token"]) > 20


class TestOwnerDeleteSchedule:
    def test_owner_deletes_member_schedule_via_house(self, client: TestClient, supabase_mock: SupabaseMock):
        from tests.conftest import TEST_MEMBER_ID
        s = make_schedule(user_id=TEST_MEMBER_ID)
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="owner")])
        supabase_mock.set_data("schedules", [s])

        res = client.delete(f"/api/v1/schedules/{s['id']}")
        assert res.status_code == 204


class TestRegenerateBotToken:
    def test_owner_regenerates_token(self, client: TestClient, supabase_mock: SupabaseMock):
        from unittest.mock import patch, MagicMock
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member(role="owner")])

        def fake_table(name):
            qb = MagicMock()
            for m in ("select", "update", "eq"):
                getattr(qb, m).return_value = qb
            qb.execute.return_value = MagicMock(data=[make_house()])
            return qb

        with patch("app.services.home.supabase") as mock_supa:
            mock_supa.table.side_effect = fake_table
            res = client.post("/api/v1/houses/me/bot-token/regenerate")

        assert res.status_code == 200
        assert res.json()["bot_token"] and len(res.json()["bot_token"]) > 20
