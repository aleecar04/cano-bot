import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, ActivityIndicator,
  Modal, ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { sendCommand, waitForCommand, getDevice, refreshDevice, type DeviceDto } from '@/api/devices';
import { friendlyError } from '@/utils/friendly-error';
import { Toast } from '@/components/ui/toast';
import { DeviceEditModal } from '@/components/devices/device-edit-modal';
import { deviceIcon, deviceColor } from '@/utils/device-icons';
import { TV_APPS } from '@/utils/device-actions';

const WOL_TYPES = new Set(['SmartTV']);

function isActionDisabled(
  action: string,
  is_online: boolean,
  state: Record<string, unknown>,
  type: string,
): boolean {
  const power = state.power as string | undefined;
  const knownState = power === 'on' || power === 'off';
  if (!knownState) return false;

  if (action === 'encender') {
    // Tele apagada/inalcanzable: permitir Encender (Wake-on-LAN), no reporta estado fiable.
    if (WOL_TYPES.has(type) && !is_online) return false;
    return is_online && power === 'on';
  }
  if (action === 'apagar') return !is_online || power !== 'on';
  return !is_online || power !== 'on';
}

interface LinkedDevice {
  id: string;
  name: string;
  type: string;
  ip: string | null;
  mac?: string | null;
  is_online: boolean;
  state: Record<string, unknown>;
  room_id?: string | null;
  location?: string;
}

interface LinkedDeviceItemProps {
  device: LinkedDevice;
  onUnlink: (deviceId: string, deviceName: string) => void;
  onDeviceUpdate?: (updated: DeviceDto) => void;
  onEditSuccess?: (updated: DeviceDto) => void;
}

type Accion = {
  action: string;
  icon: string;
  label: string;
  payload?: Record<string, unknown>;
  picker?: 'volumen' | 'app';
};

const TV_VOLUMES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

const LUZ_COLORES: { name: string; hex: string }[] = [
  { name: 'rojo',     hex: '#FF2020' },
  { name: 'naranja',  hex: '#FF6400' },
  { name: 'amarillo', hex: '#FFC800' },
  { name: 'verde',    hex: '#00C800' },
  { name: 'cyan',     hex: '#00C8FF' },
  { name: 'azul',     hex: '#0000FF' },
  { name: 'morado',   hex: '#8000C8' },
  { name: 'violeta',  hex: '#9400D3' },
  { name: 'rosa',     hex: '#FF1493' },
  { name: 'blanco',   hex: '#FFFFFF' },
];

const _BULB_TYPES      = new Set(['Luz', 'light']);
const _TUYA_BULB_TYPES = new Set(['Luz']);

function kelvinToHex(k: number): string {
  const c = Math.max(2700, Math.min(6500, k));
  if (c <= 4000) {
    const t = (c - 2700) / 1300;
    return `rgb(${Math.round(249 + t * (251 - 249))},${Math.round(115 + t * (191 - 115))},${Math.round(22 + t * (36 - 22))})`;
  }
  const t = (c - 4000) / 2500;
  return `rgb(${Math.round(251 + t * (147 - 251))},${Math.round(191 + t * (197 - 191))},${Math.round(36 + t * (253 - 36))})`;
}

function closestTempPreset(k: number): number {
  if (k <= 3350) return 2700;
  if (k <= 5250) return 4000;
  return 6500;
}

const TV_ACCIONES: Accion[] = [
  { action: 'encender',      icon: 'power',           label: 'Encender' },
  { action: 'apagar',        icon: 'power-outline',   label: 'Apagar' },
  { action: 'subir_volumen', icon: 'volume-high',     label: 'Vol +' },
  { action: 'bajar_volumen', icon: 'volume-low',      label: 'Vol -' },
  { action: 'mute',          icon: 'volume-mute',     label: 'Mute' },
  { action: 'set_volumen',   icon: 'options-outline', label: 'Volumen', picker: 'volumen' },
  { action: 'abrir_app',     icon: 'apps-outline',    label: 'Abrir app', picker: 'app' },
];

const LUZ_ACCIONES: Accion[] = [
  { action: 'encender', icon: 'sunny',        label: 'Encender' },
  { action: 'apagar',   icon: 'moon-outline', label: 'Apagar' },
];

const SWITCH_ACCIONES: Accion[] = [
  { action: 'encender', icon: 'power',         label: 'Encender' },
  { action: 'apagar',   icon: 'power-outline', label: 'Apagar' },
];

const MEDIA_ACCIONES: Accion[] = [
  { action: 'encender',      icon: 'play',            label: 'Play' },
  { action: 'apagar',        icon: 'pause',           label: 'Pausa' },
  { action: 'subir_volumen', icon: 'volume-high',     label: 'Vol +' },
  { action: 'bajar_volumen', icon: 'volume-low',      label: 'Vol -' },
  { action: 'mute',          icon: 'volume-mute',     label: 'Mute' },
  { action: 'set_volumen',   icon: 'options-outline', label: 'Volumen', picker: 'volumen' },
];

const ACCIONES: Record<string, Accion[]> = {
  SmartTV:      TV_ACCIONES,
  Luz:          LUZ_ACCIONES,
  Enchufe:      SWITCH_ACCIONES,
  IoT:          SWITCH_ACCIONES,
  light:        LUZ_ACCIONES,
  switch:       SWITCH_ACCIONES,
  climate:      SWITCH_ACCIONES,
  media_player: MEDIA_ACCIONES,
};

const DEFAULT_ACCIONES: Accion[] = [
  { action: 'encender', icon: 'power',         label: 'Encender' },
  { action: 'apagar',   icon: 'power-outline', label: 'Apagar' },
];

export const LinkedDeviceItem: React.FC<LinkedDeviceItemProps> = ({
  device, onUnlink, onDeviceUpdate, onEditSuccess,
}) => {
  const [loadingAccion, setLoadingAccion] = useState<string | null>(null);
  const [expanded, setExpanded]           = useState(false);
  const [picker, setPicker]               = useState<'volumen' | 'app' | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [refreshing, setRefreshing]       = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'error' } | null>(null);

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await refreshDevice(device.id);
      await new Promise((r) => setTimeout(r, 2500));
      const updated = await getDevice(device.id);
      onDeviceUpdate?.(updated);
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setRefreshing(false);
    }
  };

  const acciones     = ACCIONES[device.type] ?? DEFAULT_ACCIONES;
  const isBulb       = _BULB_TYPES.has(device.type);
  const hasTuyaColor = _TUYA_BULB_TYPES.has(device.type);
  const isSensor     = device.type === 'Sensor' || device.type === 'sensor';

  const handleAccion = async (action: string, payload: Record<string, unknown> = {}) => {
    setLoadingAccion(action);
    try {
      const { command_id } = await sendCommand(device.id, action, payload);
      const cmd = await waitForCommand(command_id);
      if (cmd.status === 'failed') {
        setToast({ message: cmd.error || 'Error ejecutando comando', variant: 'error' });
      } else {
        setToast({ message: 'Comando ejecutado correctamente', variant: 'success' });
        try {
          const updated = await getDevice(device.id);
          onDeviceUpdate?.(updated);
        } catch {
          // non-critical — device will refresh on next poll
        }
      }
    } catch (err) {
      const msg = String(err).includes('timeout')
        ? 'El dispositivo no respondió a tiempo'
        : friendlyError(err);
      setToast({ message: msg, variant: 'error' });
    } finally {
      setLoadingAccion(null);
    }
  };

  const handlePickerAccion = (a: Accion) => {
    if (a.picker) { setPicker(a.picker); return; }
    handleAccion(a.action, a.payload ?? {});
  };

  const icon  = deviceIcon(device.type);
  const color = deviceColor(device.type);

  return (
    <View className="bg-bg-secondary border border-border rounded-xl p-4">
      {/* Cabecera */}
      <View className="flex-row items-center justify-between">
        <View className="flex-row items-center gap-3 flex-1">
          <View
            style={{ backgroundColor: `${color}20`, borderColor: `${color}40`, borderWidth: 1 }}
            className="w-9 h-9 rounded-xl items-center justify-center"
          >
            <Ionicons name={icon as any} size={18} color={color} />
          </View>
          <View className="flex-1">
            <View className="flex-row items-center gap-2 flex-wrap">
              <Text className="text-text font-semibold text-sm">{device.name}</Text>
              <View className={`px-2 py-0.5 rounded-full ${device.is_online ? 'bg-green-500/20' : 'bg-bg'}`}>
                <Text className={`text-xs font-semibold ${device.is_online ? 'text-green-400' : 'text-text-secondary'}`}>
                  {device.is_online ? 'Disponible' : 'No disponible'}
                </Text>
              </View>
              {(device.state?.power === 'on' || device.state?.power === 'off') && (
                <View className={`px-2 py-0.5 rounded-full ${device.state.power === 'on' ? 'bg-blue-500/20' : 'bg-bg'}`}>
                  <Text className={`text-xs font-semibold ${device.state.power === 'on' ? 'text-blue-400' : 'text-text-secondary'}`}>
                    {device.state.power === 'on' ? 'Encendido' : 'Apagado'}
                  </Text>
                </View>
              )}
              {typeof device.state?.volume === 'number' && (
                <View className="px-2 py-0.5 rounded-full bg-bg">
                  <Text className="text-xs font-semibold text-text-secondary">
                    Vol. {device.state.volume}
                  </Text>
                </View>
              )}
            </View>
            <Text className="text-text-secondary text-xs mt-0.5">{device.type}</Text>
          </View>
        </View>

        <View className="flex-row gap-2">
          <TouchableOpacity
            className="bg-slate-500/20 rounded-lg px-3 py-2"
            onPress={handleRefresh}
            disabled={refreshing}
            activeOpacity={0.7}
          >
            {refreshing
              ? <ActivityIndicator size="small" color="#94a3b8" />
              : <Ionicons name="refresh" size={16} color="#94a3b8" />}
          </TouchableOpacity>

          <TouchableOpacity
            className="bg-slate-500/20 rounded-lg px-3 py-2"
            onPress={() => setShowEditModal(true)}
            activeOpacity={0.7}
          >
            <Ionicons name="pencil-outline" size={16} color="#94a3b8" />
          </TouchableOpacity>

          {acciones.length > 0 && (
            <TouchableOpacity
              className="bg-primary/20 rounded-lg px-3 py-2"
              onPress={() => setExpanded(!expanded)}
              activeOpacity={0.7}
            >
              <Ionicons name={expanded ? 'chevron-up' : 'chevron-down'} size={16} color="#3B82F6" />
            </TouchableOpacity>
          )}

          <TouchableOpacity
            className="bg-red-500/20 rounded-lg px-3 py-2"
            onPress={() => onUnlink(device.id, device.name)}
            activeOpacity={0.7}
          >
            <Ionicons name="trash" size={16} color="#ef4444" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Botones de acciones */}
      {expanded && (
        <View className="mt-3 pt-3 border-t border-primary/20 gap-3">

          {/* ── Sensor: mostrar lecturas en lugar de botones ── */}
          {isSensor && (
            <View className="flex-row flex-wrap gap-3">
              {device.state?.temperature !== undefined && (
                <View className="bg-bg border border-border rounded-xl px-4 py-3 items-center flex-1">
                  <Ionicons name="thermometer-outline" size={20} color="#06b6d4" />
                  <Text className="text-text font-bold text-lg mt-1">{device.state.temperature as number}°C</Text>
                  <Text className="text-text-secondary text-xs">Temperatura</Text>
                </View>
              )}
              {device.state?.humidity !== undefined && (
                <View className="bg-bg border border-border rounded-xl px-4 py-3 items-center flex-1">
                  <Ionicons name="water-outline" size={20} color="#3b82f6" />
                  <Text className="text-text font-bold text-lg mt-1">{device.state.humidity as number}%</Text>
                  <Text className="text-text-secondary text-xs">Humedad</Text>
                </View>
              )}
              {device.state?.flood !== undefined && (
                <View className={`border rounded-xl px-4 py-3 items-center flex-1 ${device.state.flood ? 'bg-red-500/15 border-red-500/30' : 'bg-bg border-border'}`}>
                  <Ionicons name="alert-circle-outline" size={20} color={device.state.flood ? '#ef4444' : '#94a3b8'} />
                  <Text className={`font-bold text-sm mt-1 ${device.state.flood ? 'text-red-400' : 'text-text-secondary'}`}>
                    {device.state.flood ? '¡Inundación!' : 'Sin inundación'}
                  </Text>
                </View>
              )}
              {device.state?.door !== undefined && (
                <View className="bg-bg border border-border rounded-xl px-4 py-3 items-center flex-1">
                  <Ionicons name="exit-outline" size={20} color="#f59e0b" />
                  <Text className="text-text font-bold text-sm mt-1 capitalize">{String(device.state.door)}</Text>
                  <Text className="text-text-secondary text-xs">Puerta</Text>
                </View>
              )}
              {!device.state?.temperature && !device.state?.humidity && !device.state?.flood && !device.state?.door && (
                <Text className="text-text-secondary text-xs">Sin lecturas — esperando polling</Text>
              )}
            </View>
          )}

          {/* ── Fila común: encender/apagar + acciones básicas ── */}
          {!isSensor && (
            <View className="flex-row flex-wrap gap-2">
              {acciones.map((a) => {
                const stateDisabled = isActionDisabled(a.action, device.is_online, device.state, device.type);
                const disabled = loadingAccion !== null || stateDisabled;
                return (
                  <TouchableOpacity
                    key={a.action}
                    className="bg-primary/20 border border-primary/30 rounded-lg px-3 py-2 flex-row items-center gap-1"
                    style={{ opacity: stateDisabled ? 0.35 : 1 }}
                    onPress={() => handlePickerAccion(a)}
                    disabled={disabled}
                    activeOpacity={0.7}
                  >
                    {loadingAccion === a.action
                      ? <ActivityIndicator size="small" color="#3B82F6" />
                      : <Ionicons name={a.icon as any} size={14} color="#3B82F6" />}
                    <Text className="text-primary text-xs font-semibold">{a.label}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}

          {/* ── Controles extendidos para bombillas ── */}
          {isBulb && (
            <>
              {/* Brillo */}
              <View>
                <View className="flex-row items-center justify-between mb-2">
                  <Text className="text-text-secondary text-xs font-semibold">Brillo</Text>
                  {typeof device.state?.brightness === 'number' && (
                    <Text className="text-text-secondary text-xs">{device.state.brightness as number}%</Text>
                  )}
                </View>
                <View className="flex-row gap-2">
                  {[25, 50, 75, 100].map((v) => {
                    const cur = device.state?.brightness as number | undefined;
                    const isActive = cur !== undefined && Math.abs(cur - v) < 13;
                    return (
                      <TouchableOpacity
                        key={v}
                        className={`flex-1 py-2 rounded-lg border items-center ${isActive ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}
                        onPress={() => handleAccion('brillo', { value: v })}
                        disabled={loadingAccion !== null}
                        activeOpacity={0.7}
                      >
                        <Text className={`text-xs font-semibold ${isActive ? 'text-indigo-400' : 'text-text-secondary'}`}>{v}%</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </View>

              {/* Temperatura */}
              <View>
                <Text className="text-text-secondary text-xs font-semibold mb-2">Temperatura</Text>
                {typeof device.state?.color_temp === 'number' && device.state?.work_mode !== 'colour' && (
                  <View style={{ height: 14, borderRadius: 7, backgroundColor: kelvinToHex(device.state.color_temp as number), marginBottom: 8 }} />
                )}
                <View className="flex-row gap-2">
                  {[
                    { label: 'Cálida', value: 2700, color: '#f97316' },
                    { label: 'Neutra', value: 4000, color: '#fbbf24' },
                    { label: 'Fría',   value: 6500, color: '#93c5fd' },
                  ].map(({ label, value, color }) => {
                    const curTemp = device.state?.color_temp as number | undefined;
                    const isActive = curTemp !== undefined
                      && device.state?.work_mode !== 'colour'
                      && closestTempPreset(curTemp) === value;
                    return (
                      <TouchableOpacity
                        key={label}
                        className={`flex-1 py-2 rounded-lg border items-center ${isActive ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}
                        onPress={() => handleAccion("temperatura_color", { value })}
                        disabled={loadingAccion !== null}
                        activeOpacity={0.7}
                      >
                        <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: color, marginBottom: 3 }} />
                        <Text className={`text-xs font-semibold ${isActive ? 'text-indigo-400' : 'text-text-secondary'}`}>{label}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </View>

              {/* Color — solo Tuya */}
              {hasTuyaColor && (
                <View>
                  <Text className="text-text-secondary text-xs font-semibold mb-2">Color</Text>
                  {typeof device.state?.color_hex === 'string' && device.state?.work_mode === 'colour' && (
                    <View className="flex-row items-center gap-2 mb-2">
                      <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: device.state.color_hex as string, borderWidth: 2, borderColor: 'rgba(255,255,255,0.35)' }} />
                      <View style={{ flex: 1, height: 14, borderRadius: 7, backgroundColor: device.state.color_hex as string, opacity: 0.55 }} />
                    </View>
                  )}
                  <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                    <View className="flex-row gap-2 pr-2">
                      {LUZ_COLORES.map(({ name, hex }) => {
                        const curHex = device.state?.color_hex as string | undefined;
                        const isActive = device.state?.work_mode === 'colour'
                          && curHex?.toLowerCase() === hex.toLowerCase();
                        return (
                          <TouchableOpacity
                            key={name}
                            style={{
                              width: isActive ? 36 : 30,
                              height: isActive ? 36 : 30,
                              borderRadius: isActive ? 18 : 15,
                              backgroundColor: hex,
                              borderWidth: isActive ? 3 : 2,
                              borderColor: isActive ? 'white' : 'rgba(255,255,255,0.2)',
                            }}
                            onPress={() => handleAccion('color_rgb', { color: name })}
                            disabled={loadingAccion !== null}
                            activeOpacity={0.7}
                          />
                        );
                      })}
                    </View>
                  </ScrollView>
                </View>
              )}
            </>
          )}
        </View>
      )}

      {/* Volumen / App picker */}
      <Modal
        visible={picker !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setPicker(null)}
      >
        <View className="flex-1 bg-black/60 items-center justify-center px-6">
          <View className="bg-bg-secondary rounded-2xl border border-border w-full max-w-sm">
            <View className="px-5 pt-5 pb-4 border-b border-border flex-row items-center justify-between">
              <Text className="text-text font-bold text-base">
                {picker === 'volumen' ? 'Establecer volumen' : 'Abrir aplicación'}
              </Text>
              <TouchableOpacity onPress={() => setPicker(null)}>
                <Ionicons name="close" size={20} color="#94a3b8" />
              </TouchableOpacity>
            </View>

            <View className="px-5 py-4 gap-2">
              {picker === 'volumen' && TV_VOLUMES.map(v => (
                <TouchableOpacity
                  key={v}
                  onPress={() => { setPicker(null); handleAccion('set_volumen', { value: v }); }}
                  className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3"
                  activeOpacity={0.7}
                >
                  <Ionicons name="volume-medium" size={20} color="#3B82F6" />
                  <Text className="text-text font-semibold text-sm">{v}%</Text>
                </TouchableOpacity>
              ))}

              {picker === 'app' && TV_APPS.map(({ app, label }) => (
                <TouchableOpacity
                  key={app}
                  onPress={() => { setPicker(null); handleAccion('abrir_app', { app }); }}
                  className="bg-bg border border-border rounded-xl px-4 py-3 items-center"
                  activeOpacity={0.7}
                >
                  <Text className="text-text font-semibold text-sm">{label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>
      </Modal>

      <DeviceEditModal
        visible={showEditModal}
        device={device}
        onClose={() => setShowEditModal(false)}
        onSave={(updated) => {
          setToast({ message: 'Dispositivo actualizado', variant: 'success' });
          if (onEditSuccess) onEditSuccess(updated);
        }}
        onError={(msg) => setToast({ message: msg, variant: 'error' })}  // ← AÑADIDO
      />

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'success'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </View>
  );
};