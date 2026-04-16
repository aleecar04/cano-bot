import json
from errbot import BotPlugin, botcmd
from plugins._core import BasePlugin
from plugins._helpers import (
    get_user_id_from_jid,
    get_device,
    get_user_devices,
    calculate_expected_state,
)
from drivers import ejecutar_comando
from plugins.device_cache import device_cache
from plugins.state_sync import state_sync


class Control(BasePlugin, BotPlugin):

    @botcmd
    def control_device(self, msg, args):
        """Execute a device command. Args is a JSON string with device_id, accion, payload."""
        try:
            data = json.loads(args)
            user_id = get_user_id_from_jid(str(msg.frm))
            device = get_device(data["device_id"], user_id)

            if not device:
                return json.dumps({"ok": False, "error": "Dispositivo no encontrado"})

            resultado = ejecutar_comando(device, data["accion"], data.get("payload", {}))

            if resultado["ok"]:
                new_estado = calculate_expected_state(device, data["accion"], data.get("payload", {}))
                state = device_cache.update(
                    device_id=device["id"],
                    estado=new_estado,
                    is_online=True,
                    source="action",
                    confidence=0.9,
                )
                state_sync.mark_device_changed(device["id"], state)
            else:
                device_cache.mark_offline(device["id"])

            # Update device status in backend via webhook (not the chat message — that's
            # handled by the dispatcher after this function returns).
            self.update_device_status(device_id=device["id"], is_online=resultado["ok"])

            return json.dumps(resultado)

        except Exception as e:
            self.log.error(f"Error in control_device: {e}", exc_info=True)
            return json.dumps({"ok": False, "error": str(e)})

    @botcmd
    def list_devices(self, msg, args):
        """List all devices owned by the requesting user, enriched with cache info."""
        try:
            user_id = get_user_id_from_jid(str(msg.frm))
            devices = get_user_devices(user_id)

            devices_enriched = []
            for device in devices:
                cached = device_cache.get(device["id"])
                info = {
                    "id": device["id"],
                    "name": device["name"],
                    "type": device["type"],
                    "driver": device["driver"],
                    "is_online": device["is_online"],
                    "cached": cached is not None,
                }
                if cached:
                    info.update({
                        "cache_age_seconds": cached.age_seconds(),
                        "cache_confidence": cached.confidence,
                        "cache_is_stale": cached.is_stale(),
                        "estado": cached.estado,
                        "cache_source": cached.source,
                    })
                devices_enriched.append(info)

            return json.dumps({
                "tipo": "device_list",
                "dispositivos": devices_enriched,
                "total": len(devices_enriched),
                "cache_summary": device_cache.get_status_summary(),
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
