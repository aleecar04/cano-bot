from typing import Optional

from app.core.db import supabase
from app.core.errors import forbidden, not_found
from app.repositories.commands import command_repository
from app.repositories.houses import house_member_repository
from app.services.home import home_service
from app.services.command_kinds import classify_action_type
from app.services.push import push_service

_NOW = "now()"


def _resolve_target_user_ids(user_id: str, member_id: Optional[str]) -> str | list[str]:
    if not member_id or home_service.get_user_role(user_id) != "owner":
        return user_id
    if member_id == "all":
        return home_service.get_house_member_ids(user_id)
    house_ids = home_service.get_house_member_ids(user_id)
    return member_id if member_id in house_ids else user_id


def _send_schedule_push(row: dict, error: str | None) -> None:
    try:
        device_name = (row.get("devices") or {}).get("name", "dispositivo")
        action_map = {
            "encender": "Encender", "apagar": "Apagar",
            "brillo": "Brillo", "temperatura_color": "Temperatura color",
            "subir_volumen": "Subir volumen", "bajar_volumen": "Bajar volumen",
            "mute": "Silenciar", "set_volumen": "Ajustar volumen",
            "abrir_app": "Abrir app", "color_rgb": "Color",
        }
        action_label = action_map.get(row.get("action", ""), row.get("action", ""))
        if error:
            push_service.send_push(row["user_id"], "❌ Tarea fallida",
                      f"{action_label} {device_name}: {error}")
        else:
            push_service.send_push(row["user_id"], "✅ Tarea ejecutada",
                      f"{action_label} {device_name} completado correctamente")
    except Exception:
        pass


def _create_command(
    user_id: str,
    device_id: str | None,
    action: str,
    payload: dict = {},
    status: str = "pending",
    error: str | None = None,
    source_type: str = "conversation",
    source_id: str | None = None,
    target_type: str = "device",
    result_data: dict | None = None,
) -> str:
    result = supabase.table("commands").insert({
        "user_id":     user_id,
        "device_id":   device_id,
        "target_type": target_type,
        "action":      action,
        "payload":     payload,
        "status":      status,
        "executed_at": _NOW if status == "executed" else None,
        "error":       error,
        "result_data": result_data,
        "source_type": source_type,
        "source_id":   source_id,
    }).execute()
    return result.data[0]["id"]


class CommandsService:

    def get_command_history(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 50,
        source_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        member_id: Optional[str] = None,
    ) -> list[dict]:
        return command_repository.find_history(
            user_ids=_resolve_target_user_ids(user_id, member_id),
            source_type=source_type,
            date_from=date_from,
            date_to=date_to,
            offset=(page - 1) * limit,
            limit=limit,
        )

    def get_command_by_id(self, command_id: str, user_id: str) -> dict:
        cmd = command_repository.find_by_id_and_user(command_id, user_id)
        if not cmd:
            raise not_found("Comando no encontrado")
        return cmd

    def create_command_from_bot(self, body: dict) -> dict:
        house_id = body.pop("_authenticated_house_id", None)
        user_house = house_member_repository.find_house_id_by_user(body["user_id"])
        if user_house != house_id:
            raise forbidden("El usuario no pertenece a esta casa")

        if body.get("pending"):
            status, error = "pending", None
        else:
            error = body.get("error") or None
            status = "failed" if error else "executed"

        # target_type se deduce del action (info/system) o se fuerza a device si hay device_id.
        target_type = body.get("target_type")
        if not target_type:
            target_type = "device" if body.get("device_id") else classify_action_type(body.get("action"))

        command_id = _create_command(
            user_id=body["user_id"],
            device_id=body.get("device_id"),
            action=body["action"],
            payload=body.get("payload", {}),
            status=status,
            error=error,
            source_type=body.get("source_type") or "conversation",
            source_id=body.get("source_id") or None,
            target_type=target_type,
            result_data=body.get("result_data") or None,
        )

        if body.get("message_id"):
            supabase.table("messages").update({
                "command_id": command_id
            }).eq("id", body["message_id"]).execute()

        return {"ok": True, "command_id": command_id}

    def update_command_result(self, command_id: str, house_id: str, error: str | None, result_data: dict | None = None, response: str | None = None) -> None:
        row = command_repository.find_meta_by_id(command_id)
        if not row:
            raise not_found("Comando no encontrado")
        if house_member_repository.find_house_id_by_user(row["user_id"]) != house_id:
            raise forbidden("El comando no pertenece a esta casa")

        error = error or None
        status = "failed" if error else "executed"
        data: dict = {"status": status, "executed_at": _NOW}
        if error:
            data["error"] = error
        if result_data is not None:
            data["result_data"] = result_data
        supabase.table("commands").update(data).eq("id", command_id).execute()

        # El texto de confirmación que decide el bot va a la respuesta del MENSAJE del
        # chat (no al comando), reutilizando el mecanismo de respuestas de mensajes.
        if response:
            from app.services.messages import save_command_response
            save_command_response(command_id, response)

        if row.get("source_type") == "schedule":
            _send_schedule_push(row, error)


commands_service = CommandsService()
