from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    SupabaseMock, TEST_HOUSE_ID, TEST_USER_ID,
    make_device, make_floor, make_house, make_house_member, make_room, make_schedule,
)

_NO_CONFLICT = patch("app.services.schedules._check_conflicting_power_schedule")


def _setup_house(supabase_mock: SupabaseMock, role="owner", **house_kwargs):
    house = make_house(**house_kwargs)
    member = make_house_member(house["id"], TEST_USER_ID, role)
    supabase_mock.set_data("houses", [house])
    supabase_mock.set_data("house_members", [member])
    return house


def _no_house(supabase_mock: SupabaseMock):
    supabase_mock.set_data("house_members", [])
    supabase_mock.set_data("houses", [])


class TestGetMyHouse:
    def test_returns_house_with_floors_and_rooms(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        floor = make_floor(house["id"])
        supabase_mock.set_data("floors", [floor])
        supabase_mock.set_data("rooms", [make_room(floor["id"])])

        res = client.get("/api/v1/houses/me")

        data = res.json()
        assert res.status_code == 200
        assert data["id"] == house["id"] and len(data["floors"][0]["rooms"]) == 1



@pytest.mark.parametrize("path", [
    "/api/v1/houses/me",
    "/api/v1/houses/me/rooms",
    "/api/v1/houses/me/members",
    "/api/v1/houses/me/invite",
])
def test_returns_404_when_user_has_no_house(client: TestClient, supabase_mock: SupabaseMock, path):
    _no_house(supabase_mock)
    method = client.post if "invite" in path else client.get
    assert method(path).status_code == 404


class TestGetMyRooms:
    def test_returns_flat_room_list(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        floor = make_floor(house["id"])
        supabase_mock.set_data("floors", [floor])
        supabase_mock.set_data("rooms", [make_room(floor["id"])])
        res = client.get("/api/v1/houses/me/rooms")
        assert res.status_code == 200 and len(res.json()) == 1


class TestFloorAndRoomCreation:
    def test_owner_creates_floor(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        new_floor = make_floor(house["id"], name="Primera Planta", level=1)
        supabase_mock.set_data("floors", [new_floor])

        res = client.post("/api/v1/houses/me/floors", json={"name": "Primera Planta", "level": 1})

        assert res.status_code == 201 and res.json()["rooms"] == []

    def test_owner_creates_room(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        floor = make_floor(TEST_HOUSE_ID)
        room = make_room(floor["id"], name="Cocina")
        supabase_mock.set_data("rooms", [room])
        res = client.post(f"/api/v1/houses/floors/{floor['id']}/rooms", json={"name": "Cocina"})
        assert res.status_code == 201 and res.json()["name"] == "Cocina"

    def test_member_cannot_add_floor(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock, role="member")
        supabase_mock.set_data("floors", [])
        res = client.post("/api/v1/houses/me/floors", json={"name": "Planta 1", "level": 1})
        assert res.status_code == 403


class TestGroupActions:
    @pytest.mark.parametrize("path, action", [
        ("/api/v1/houses/rooms/room-1/action", "brillo"),
        ("/api/v1/houses/floors/floor-1/action", "set_volumen"),
    ])
    def test_unsupported_action_returns_400(self, client: TestClient, path, action):
        assert client.post(path, json={"action": action}).status_code == 400



class TestMemberManagement:
    def test_kick_requires_owner_role(self, client: TestClient, supabase_mock: SupabaseMock):
        from tests.conftest import TEST_MEMBER_ID
        _setup_house(supabase_mock, role="member")
        res = client.delete(f"/api/v1/houses/me/members/{TEST_MEMBER_ID}")
        assert res.status_code == 403

    def test_member_and_owner_can_leave(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock, role="member")
        assert client.delete("/api/v1/houses/me/leave").status_code == 204

        _setup_house(supabase_mock, role="owner")
        assert client.delete("/api/v1/houses/me/leave").status_code == 204

    def test_setup_rejects_if_user_already_in_house(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        res = client.post("/api/v1/houses/setup", json={"bot_jid": "other-bot@xmpp.test"})
        assert res.status_code == 409


class TestHouseMembers:
    def test_get_members_returns_list(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("base_user", [{"id": TEST_USER_ID, "username": "testuser"}])
        res = client.get("/api/v1/houses/me/members")
        assert res.status_code == 200 and isinstance(res.json(), list)


class TestGroupSchedules:
    @pytest.mark.parametrize("path, setup", [
        ("/api/v1/houses/rooms/room-1/schedule", {"devices": []}),
        ("/api/v1/houses/floors/floor-1/schedule", {"rooms": []}),
        ("/api/v1/houses/floors/floor-1/schedule", {"rooms": [{"id": "r1"}], "devices": []}),
    ])
    def test_group_schedule_returns_404_when_target_empty(self, client: TestClient, supabase_mock: SupabaseMock, path, setup):
        for table, data in setup.items():
            supabase_mock.set_data(table, data)
        res = client.post(path, json={
            "device_id": "00000000-0000-0000-0000-000000000001",
            "name": "x", "action": "apagar",
            "cron_expr": "0 22 * * *", "is_recurring": True,
        })
        assert res.status_code == 404

    def test_room_schedule_creates_for_each_device(self, client: TestClient, supabase_mock: SupabaseMock):
        import uuid
        d1 = make_device(id=str(uuid.uuid4()))
        d2 = make_device(id=str(uuid.uuid4()), mac="BB:BB:BB:BB:BB:BB")
        _setup_house(supabase_mock)
        supabase_mock.set_data("devices", [d1, d2])
        supabase_mock.set_data("schedules", [make_schedule()])

        with _NO_CONFLICT:
            res = client.post("/api/v1/houses/rooms/room-1/schedule", json={
                "device_id": d1["id"], "name": "Apagar todo",
                "action": "apagar", "cron_expr": "0 22 * * *", "is_recurring": True,
            })
        assert res.status_code == 200 and res.json()["ok"] is True


class TestDeleteFloorRoom:
    def test_owner_deletes_floor_and_room(self, client: TestClient, supabase_mock: SupabaseMock):
        house = _setup_house(supabase_mock)
        floor = make_floor(house["id"])
        room = make_room(floor["id"])
        supabase_mock.set_data("floors", [floor])
        supabase_mock.set_data("rooms", [room])

        assert client.delete(f"/api/v1/houses/floors/{floor['id']}/rooms/{room['id']}").status_code in (204, 404)
        assert client.delete(f"/api/v1/houses/floors/{floor['id']}").status_code in (204, 404)


class TestInvitationCodes:
    def test_generate_invite_code(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("house_invitations", [{"id": "inv-1", "code": "ABC123"}])
        res = client.post("/api/v1/houses/me/invite")
        data = res.json()
        assert res.status_code == 200 and "code" in data and data["expires_in_hours"] == 24

    def test_join_with_valid_code(self, client: TestClient, supabase_mock: SupabaseMock):
        from datetime import datetime, timedelta, timezone
        house = make_house()
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("house_invitations", [{
            "id": "inv-1", "house_id": house["id"], "code": "ABC123",
            "used_at": None,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }])
        res = client.post("/api/v1/houses/join", json={"code": "ABC123"})
        assert res.status_code == 200 and res.json()["ok"] is True



def _fake_table_factory(name_filter, data):
    def fake_table(name):
        qb = MagicMock()
        for m in ("select", "insert", "update", "upsert", "eq"):
            getattr(qb, m).return_value = qb
        qb.execute.return_value = MagicMock(data=data if name == name_filter else [])
        return qb
    return fake_table


class TestHouseSetup:
    def test_setup_creates_house_and_returns_bot_token(self, client: TestClient, supabase_mock: SupabaseMock):
        new_house = make_house()
        supabase_mock.set_data("house_members", [])
        with patch("app.services.home.supabase") as mock_supa:
            mock_supa.table.side_effect = _fake_table_factory("houses", [new_house])
            res = client.post("/api/v1/houses/setup", json={"name": "Mi Casa"})

        body = res.json()
        assert res.status_code == 201 and "house_id" in body
        assert body["bot_token"] and len(body["bot_token"]) > 20


class TestRegenerateBotToken:
    def test_owner_regenerates_token(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        with patch("app.services.home.supabase") as mock_supa:
            mock_supa.table.side_effect = _fake_table_factory("houses", [make_house()])
            res = client.post("/api/v1/houses/me/bot-token/regenerate")
        assert res.status_code == 200 and len(res.json()["bot_token"]) > 20


class TestOwnerDeleteSchedule:
    def test_owner_deletes_member_schedule(self, client: TestClient, supabase_mock: SupabaseMock):
        from tests.conftest import TEST_MEMBER_ID
        s = make_schedule(user_id=TEST_MEMBER_ID)
        _setup_house(supabase_mock)
        supabase_mock.set_data("schedules", [s])
        assert client.delete(f"/api/v1/schedules/{s['id']}").status_code == 204
