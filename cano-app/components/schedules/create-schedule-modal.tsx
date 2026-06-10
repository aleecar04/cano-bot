import { useEffect, useState } from 'react';
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  ScrollView, ActivityIndicator, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type DeviceDto } from '@/api/devices';
import { type CreateScheduleParams } from '@/api/schedules';
import {
  getActionsForType,
  LUZ_COLORES, TV_APPS, TV_VOLUMES,
  BRIGHTNESS_PRESETS, TEMP_PRESETS, kelvinToHex,
} from '@/utils/device-actions';

type Frequency = 'once' | 'daily' | 'custom';

const FREQ_OPTIONS: { value: Frequency; label: string; icon: string }[] = [
  { value: 'once',   label: 'Una vez',       icon: 'calendar-outline' },
  { value: 'daily',  label: 'Cada día',      icon: 'repeat' },
  { value: 'custom', label: 'Personalizado', icon: 'settings-outline' },
];

const USER_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

function buildCronExpr(freq: Frequency, date: Date): string {
  const h = date.getHours();
  const m = date.getMinutes();
  return freq === 'daily' || freq === 'custom' ? `${m} ${h} * * *` : '';
}

function formatShortDate(d: Date): string {
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function toTimeStr(d: Date): string {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

interface Props {
  visible: boolean;
  devices: DeviceDto[];
  saving: boolean;
  onClose: () => void;
  onConfirm: (params: CreateScheduleParams) => void;
}

export function CreateScheduleModal({ visible, devices, saving, onClose, onConfirm }: Readonly<Props>) {
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedAction, setSelectedAction] = useState('encender');
  const [frequency, setFrequency]           = useState<Frequency>('daily');
  const [dateStr, setDateStr]       = useState(toDateStr(new Date()));
  const [timeStr, setTimeStr]       = useState(toTimeStr(new Date()));
  const [endDateStr, setEndDateStr] = useState(toDateStr(new Date()));
  const [name, setName]             = useState('');

  // payload state — presets only
  const [brightnessVal, setBrightnessVal] = useState(75);
  const [colorTempVal, setColorTempVal]   = useState(4000);
  const [volumeVal, setVolumeVal]         = useState(50);
  const [selectedApp, setSelectedApp]     = useState('netflix');
  const [selectedColor, setSelectedColor] = useState('rojo'); // color name

  const selectedDeviceObj = devices.find((d) => d.id === selectedDevice);
  const isTuya            = selectedDeviceObj?.driver === 'tuya';
  const availableActions  = getActionsForType(selectedDeviceObj?.type ?? '', isTuya);
  const currentActionDef  = availableActions.find((a) => a.accion === selectedAction);

  const handleSelectDevice = (id: string) => {
    setSelectedDevice(id);
    const dev     = devices.find((d) => d.id === id);
    const actions = getActionsForType(dev?.type ?? '', dev?.driver === 'tuya');
    if (!actions.find((a) => a.accion === selectedAction)) {
      setSelectedAction(actions[0]?.accion ?? 'encender');
    }
  };

  useEffect(() => {
    if (!visible) return;
    const now = new Date();
    setDateStr(toDateStr(now));
    setTimeStr(toTimeStr(now));
    setName('');
    setSelectedDevice('');
    setSelectedAction('encender');
    setFrequency('daily');
    setBrightnessVal(75);
    setColorTempVal(4000);
    setVolumeVal(50);
    setSelectedApp('netflix');
    setSelectedColor('rojo');
    setEndDateStr(toDateStr(now));
  }, [visible]);

  const buildPayload = (): Record<string, unknown> => {
    switch (currentActionDef?.payloadType) {
      case 'brightness': return { valor: brightnessVal };
      case 'color_temp': return { valor: colorTempVal };
      case 'volumen':    return { valor: volumeVal };
      case 'app':        return { app: selectedApp };
      case 'color':      return { color: selectedColor };
      default:           return {};
    }
  };

  const handleConfirm = () => {
    if (!selectedDevice) return;
    const actionDef   = availableActions.find((a) => a.accion === selectedAction);
    const actionLabel = actionDef?.label ?? selectedAction;
    const deviceName  = selectedDeviceObj?.name ?? 'Dispositivo';
    const finalName   = name.trim() || `${actionLabel} ${deviceName}`;
    const payload     = buildPayload();
    const dt          = new Date(`${dateStr}T${timeStr}:00`);

    if (frequency === 'once') {
      onConfirm({ device_id: selectedDevice, name: finalName, action: selectedAction, payload, run_at: dt.toISOString(), timezone: USER_TIMEZONE });
    } else if (frequency === 'custom') {
      const endDt      = new Date(`${endDateStr}T${timeStr}:00`);
      const rangeLabel = `${formatShortDate(dt)} → ${formatShortDate(endDt)}`;
      const nameWithRange = name.trim() ? `${name.trim()} (${rangeLabel})` : `${actionLabel} ${deviceName} (${rangeLabel})`;
      onConfirm({ device_id: selectedDevice, name: nameWithRange, action: selectedAction, payload, cron_expr: buildCronExpr(frequency, dt), timezone: USER_TIMEZONE });
    } else {
      onConfirm({ device_id: selectedDevice, name: finalName, action: selectedAction, payload, cron_expr: buildCronExpr(frequency, dt), timezone: USER_TIMEZONE });
    }
  };

  const todayStr = toDateStr(new Date());
  const isValid = !!selectedDevice && (
    frequency !== 'custom' ||
    (dateStr >= todayStr && endDateStr > dateStr)
  );

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={() => { if (!saving) onClose(); }}>
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary rounded-t-3xl border-t border-border pb-8">

          {/* Header */}
          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <Text className="text-text text-base font-bold">Nueva tarea programada</Text>
            <TouchableOpacity onPress={onClose} disabled={saving} activeOpacity={0.7}>
              <Ionicons name="close" size={22} color="#94a3b8" />
            </TouchableOpacity>
          </View>

          <ScrollView className="px-5 pt-4" showsVerticalScrollIndicator={false} style={{ maxHeight: 520 }}>

            {/* Nombre */}
            <Text className="text-text text-sm font-semibold mb-2">Nombre (opcional)</Text>
            <TextInput
              className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm mb-5"
              style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
              value={name} onChangeText={setName}
              placeholder="Ej. Encender tele por la noche"
              placeholderTextColor="#64748b" editable={!saving}
              maxLength={50}
            />

            {/* Dispositivo */}
            <Text className="text-text text-sm font-semibold mb-2">Dispositivo</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-5">
              <View className="flex-row gap-2 pr-4">
                {devices.map((d) => (
                  <TouchableOpacity key={d.id} onPress={() => handleSelectDevice(d.id)} activeOpacity={0.7}
                    className={`px-3 py-2 rounded-lg border ${selectedDevice === d.id ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                    <Text className={`text-xs font-semibold ${selectedDevice === d.id ? 'text-white' : 'text-text-secondary'}`}>{d.name}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            {/* Acción */}
            {selectedDevice && (
              <>
                <Text className="text-text text-sm font-semibold mb-2">Acción</Text>
                <View className="flex-row flex-wrap gap-2 mb-5">
                  {availableActions.map((a) => (
                    <TouchableOpacity key={a.accion} onPress={() => setSelectedAction(a.accion)} activeOpacity={0.7}
                      className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${selectedAction === a.accion ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                      <Ionicons name={a.icon as any} size={14} color={selectedAction === a.accion ? 'white' : '#94a3b8'} />
                      <Text className={`text-xs font-semibold ${selectedAction === a.accion ? 'text-white' : 'text-text-secondary'}`}>{a.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}

            {/* ── Payload: Brillo ── */}
            {currentActionDef?.payloadType === 'brightness' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Brillo</Text>
                <View className="flex-row gap-2">
                  {BRIGHTNESS_PRESETS.map((v) => (
                    <TouchableOpacity key={v} onPress={() => setBrightnessVal(v)} activeOpacity={0.7}
                      className={`flex-1 py-2 rounded-lg border items-center ${brightnessVal === v ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}>
                      <Text className={`text-xs font-semibold ${brightnessVal === v ? 'text-indigo-400' : 'text-text-secondary'}`}>{v}%</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* ── Payload: Temperatura ── */}
            {currentActionDef?.payloadType === 'color_temp' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Temperatura de color</Text>
                <View style={{ height: 14, borderRadius: 7, backgroundColor: kelvinToHex(colorTempVal), marginBottom: 8 }} />
                <View className="flex-row gap-2">
                  {TEMP_PRESETS.map(({ label, valor, color }) => (
                    <TouchableOpacity key={valor} onPress={() => setColorTempVal(valor)} activeOpacity={0.7}
                      className={`flex-1 py-2 rounded-lg border items-center ${colorTempVal === valor ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}>
                      <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: color, marginBottom: 3 }} />
                      <Text className={`text-xs font-semibold ${colorTempVal === valor ? 'text-indigo-400' : 'text-text-secondary'}`}>{label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* ── Payload: Color ── */}
            {currentActionDef?.payloadType === 'color' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Color</Text>
                {(() => {
                  const cur = LUZ_COLORES.find((c) => c.name === selectedColor);
                  return cur ? (
                    <View className="flex-row items-center gap-2 mb-3">
                      <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: cur.hex, borderWidth: 2, borderColor: 'rgba(255,255,255,0.35)' }} />
                      <View style={{ flex: 1, height: 14, borderRadius: 7, backgroundColor: cur.hex, opacity: 0.55 }} />
                    </View>
                  ) : null;
                })()}
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View className="flex-row gap-2 pr-2">
                    {LUZ_COLORES.map(({ name, hex }) => {
                      const isActive = selectedColor === name;
                      return (
                        <TouchableOpacity key={name} onPress={() => setSelectedColor(name)} activeOpacity={0.7}
                          style={{ width: isActive ? 36 : 30, height: isActive ? 36 : 30, borderRadius: isActive ? 18 : 15, backgroundColor: hex, borderWidth: isActive ? 3 : 2, borderColor: isActive ? 'white' : 'rgba(255,255,255,0.2)' }} />
                      );
                    })}
                  </View>
                </ScrollView>
              </View>
            )}

            {/* ── Payload: Volumen ── */}
            {currentActionDef?.payloadType === 'volumen' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Volumen</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View className="flex-row gap-2 pr-4">
                    {TV_VOLUMES.map((v) => (
                      <TouchableOpacity key={v} onPress={() => setVolumeVal(v)} activeOpacity={0.7}
                        className={`px-3 py-2 rounded-lg border ${volumeVal === v ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                        <Text className={`text-xs font-bold ${volumeVal === v ? 'text-white' : 'text-text-secondary'}`}>{v}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </ScrollView>
              </View>
            )}

            {/* ── Payload: App ── */}
            {currentActionDef?.payloadType === 'app' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Aplicación</Text>
                <View className="flex-row flex-wrap gap-2">
                  {TV_APPS.map((ap) => (
                    <TouchableOpacity key={ap.app} onPress={() => setSelectedApp(ap.app)} activeOpacity={0.7}
                      className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${selectedApp === ap.app ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                      <Ionicons name={ap.icon as any} size={14} color={selectedApp === ap.app ? 'white' : '#94a3b8'} />
                      <Text className={`text-xs font-semibold ${selectedApp === ap.app ? 'text-white' : 'text-text-secondary'}`}>{ap.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* Frecuencia */}
            <Text className="text-text text-sm font-semibold mb-2">Frecuencia</Text>
            <View className="flex-row flex-wrap gap-2 mb-5">
              {FREQ_OPTIONS.map((f) => (
                <TouchableOpacity key={f.value} onPress={() => setFrequency(f.value)} activeOpacity={0.7}
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${frequency === f.value ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                  <Ionicons name={f.icon as any} size={14} color={frequency === f.value ? 'white' : '#94a3b8'} />
                  <Text className={`text-xs font-semibold ${frequency === f.value ? 'text-white' : 'text-text-secondary'}`}>{f.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {frequency === 'custom' && (
              <View className="mb-5">
                {/* Hora única */}
                <Text className="text-text text-sm font-semibold mb-2">Hora de ejecución</Text>
                <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-4">
                  <Ionicons name="time-outline" size={18} color="#6366f1" />
                  {/* @ts-ignore */}
                  <input type="time" value={timeStr} onChange={(e: any) => setTimeStr(e.target.value)} disabled={saving}
                    style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
                </View>

                {/* Fecha de inicio */}
                <Text className="text-text text-sm font-semibold mb-2">Desde</Text>
                <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-1">
                  <Ionicons name="calendar-outline" size={18} color="#6366f1" />
                  {/* @ts-ignore */}
                  <input type="date" value={dateStr} min={toDateStr(new Date())} onChange={(e: any) => setDateStr(e.target.value)} disabled={saving}
                    style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
                </View>
                {dateStr < toDateStr(new Date()) && (
                  <Text className="text-red-400 text-xs mb-3">La fecha de inicio no puede ser anterior a hoy</Text>
                )}

                {/* Fecha de fin */}
                <Text className="text-text text-sm font-semibold mb-2 mt-3">Hasta</Text>
                <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-1">
                  <Ionicons name="calendar-outline" size={18} color="#f59e0b" />
                  {/* @ts-ignore */}
                  <input type="date" value={endDateStr} min={dateStr} onChange={(e: any) => setEndDateStr(e.target.value)} disabled={saving}
                    style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
                </View>
                {endDateStr <= dateStr && (
                  <Text className="text-red-400 text-xs">La fecha de fin debe ser posterior al inicio</Text>
                )}
              </View>
            )}

            {frequency === 'once' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Fecha</Text>
                <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3">
                  <Ionicons name="calendar-outline" size={18} color="#6366f1" />
                  {/* @ts-ignore */}
                  <input type="date" value={dateStr} onChange={(e) => setDateStr(e.target.value)} disabled={saving}
                    style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
                </View>
              </View>
            )}

            {frequency !== 'custom' && (
              <View className="mb-6">
                <Text className="text-text text-sm font-semibold mb-2">Hora</Text>
                <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3">
                  <Ionicons name="time-outline" size={18} color="#6366f1" />
                  {/* @ts-ignore */}
                  <input type="time" value={timeStr} onChange={(e: any) => setTimeStr(e.target.value)} disabled={saving}
                    style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
                </View>
              </View>
            )}

          </ScrollView>

          {/* Botones */}
          <View className="flex-row gap-3 px-5 pt-2">
            <TouchableOpacity className="flex-1 bg-red-500 rounded-xl py-3 items-center"
              onPress={onClose} disabled={saving} activeOpacity={0.7}>
              <Text className="text-white font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${!isValid || saving ? 'bg-indigo-500/40' : 'bg-indigo-500'}`}
              onPress={handleConfirm} disabled={!isValid || saving} activeOpacity={0.8}>
              {saving ? <ActivityIndicator color="white" size="small" /> : <Ionicons name="checkmark" size={16} color="white" />}
              <Text className="text-white font-semibold text-sm">{saving ? 'Guardando...' : 'Crear tarea'}</Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>
    </Modal>
  );
}
