"""
Plugin de administración para monitorear sincronización de dispositivos
Comandos para debugging y monitoreo del caché y estado de sincronización
"""
import json
from errbot import BotPlugin, botcmd
from plugins.device_cache import device_cache
from plugins.state_sync import state_sync


class SystemAdmin(BotPlugin):
    """Comandos administrativos del sistema domótico"""
    
    @botcmd
    def cache_devices(self, msg, args):
        """Lista todos los dispositivos en caché"""
        try:
            cached_devices = {}
            for device_id, state in device_cache.get_all().items():
                cached_devices[device_id] = state.to_dict()
            
            return json.dumps({
                "ok": True,
                "cached_devices": cached_devices,
                "total": len(cached_devices)
            }, indent=2)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    @botcmd
    def clear_cache(self, msg, args):
        """Limpia la caché de dispositivos"""
        try:
            if args.strip():
                # Limpiar dispositivo específico
                device_cache.clear(args.strip())
                return json.dumps({"ok": True, "message": f"Caché de {args.strip()} limpiada"})
            else:
                # Limpiar todo
                device_cache.clear()
                return json.dumps({"ok": True, "message": "Caché completamente limpiada"})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    @botcmd
    def sync_stats(self, msg, args):
        """Muestra estadísticas de sincronización"""
        try:
            stats = state_sync.get_stats()
            return json.dumps({
                "ok": True,
                "sync": stats
            }, indent=2)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
    
    @botcmd
    def force_sync(self, msg, args):
        """Fuerza una sincronización completa con backend"""
        try:
            # Marcar todos los dispositivos en caché para sincronizar
            for device_id, state in device_cache.get_all().items():
                state_sync.mark_device_changed(device_id, state)
            
            return json.dumps({
                "ok": True,
                "message": f"{len(device_cache.get_all())} dispositivos marcados para sincronizar"
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
