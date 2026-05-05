import { useEffect, useState } from 'react';
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  ScrollView, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type DeviceDto } from '@/api/devices';
import { type CreateScheduleParams } from '@/api/schedules';

type Frequency = 'once' | 'daily' | 'weekdays' | 'weekends';

const FREQ_OPTIONS: { value: Frequency; label: string; icon: string }[] = [
  { value: 'once',     label: 'Una vez',        icon: 'calendar-outline' },
  { value: 'daily',    label: 'Cada día',        icon: 'repeat' },
  { value: 'weekdays', label: 'Días laborables', icon: 'briefcase-outline' },
  { value: 'weekends', label: 'Fin de semana',   icon: 'sunny-outline' },
];

const ALL_ACTIONS = [
  { value: 'encender',         label: 'Encender',        icon: 'power',             types: null },
  { value: 'apagar',           label: 'Apagar',          icon: 'power-outline',     types: null },
  { value: 'brillo',           label: 'Brillo',          icon: 'sunny',             types: ['Luz','light'] },
  { value: 'temperatura_color',label: 'Temperatura',     icon: 'thermometer-outline', types: ['Luz','light'] },
  { value: 'subir_volumen',    label: 'Subir volumen',   icon: 'volume-high',       types: ['SmartTV','media_player','Altavoz'] },
  { value: 'bajar_volumen',    label: 'Bajar volumen',   icon: 'volume-low',        types: ['SmartTV','media_player','Altavoz'] },
  { value: 'mute',             label: 'Silenciar',       icon: 'volume-mute',       types: ['SmartTV','media_player','Altavoz'] },
];

function actionsForType(type: string | undefined) {
  if (!type) return ALL_ACTIONS;
  return ALL_ACTIONS.filter((a) => a.types === null || a.types.includes(type));
}

const USER_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

function buildCronExpr(freq: Frequency, date: Date): string {
  const h = date.getHours();
  const m = date.getMinutes();
  switch (freq) {
    case 'daily':    return `${m} ${h} * * *`;
    case 'weekdays': return `${m} ${h} * * 1-5`;
    case 'weekends': return `${m} ${h} * * 0,6`;
    default:         return '';
  }
}

function toDateStr(d: Date): string {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
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

  const selectedDeviceType = devices.find((d) => d.id === selectedDevice)?.type;
  const availableActions   = actionsForType(selectedDeviceType);

  const handleSelectDevice = (id: string) => {
    setSelectedDevice(id);
    const type = devices.find((d) => d.id === id)?.type;
    const actions = actionsForType(type);
    if (!actions.find((a) => a.value === selectedAction)) {
      setSelectedAction('encender');
    }
  };
  const [frequency, setFrequency]           = useState<Frequency>('daily');
  const [dateStr, setDateStr]               = useState(toDateStr(new Date()));
  const [timeStr, setTimeStr]               = useState(toTimeStr(new Date()));
  const [brightnessVal, setBrightnessVal]   = useState(80);
  const [name, setName]                     = useState('');

  useEffect(() => {
    if (!visible) return;
    const now = new Date();
    setDateStr(toDateStr(now));
    setTimeStr(toTimeStr(now));
    setName('');
    setSelectedDevice('');
    setSelectedAction('encender');
    setFrequency('daily');
    setBrightnessVal(80);
  }, [visible]);

  const handleConfirm = () => {
    if (!selectedDevice) return;
    const actionLabel = ALL_ACTIONS.find((a) => a.value === selectedAction)?.label ?? selectedAction;
    const deviceName  = devices.find((d) => d.id === selectedDevice)?.name ?? 'Dispositivo';
    const finalName   = name.trim() || `${actionLabel} ${deviceName}`;
    const payload: Record<string, unknown> = selectedAction === 'brillo' ? { valor: brightnessVal } : {};

    const dt = new Date(`${dateStr}T${timeStr}:00`);
    if (frequency === 'once') {
      onConfirm({
        device_id: selectedDevice,
        name:      finalName,
        action:    selectedAction,
        payload,
        run_at:    dt.toISOString(),
        timezone:  USER_TIMEZONE,
      });
    } else {
      onConfirm({
        device_id: selectedDevice,
        name:      finalName,
        action:    selectedAction,
        payload,
        cron_expr: buildCronExpr(frequency, dt),
        timezone:  USER_TIMEZONE,
      });
    }
  };

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
              value={name}
              onChangeText={setName}
              placeholder="Ej. Encender tele por la noche"
              placeholderTextColor="#64748b"
              editable={!saving}
            />

            {/* Dispositivo */}
            <Text className="text-text text-sm font-semibold mb-2">Dispositivo</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-5">
              <View className="flex-row gap-2 pr-4">
                {devices.map((d) => (
                  <TouchableOpacity
                    key={d.id}
                    onPress={() => handleSelectDevice(d.id)}
                    className={`px-3 py-2 rounded-lg border ${
                      selectedDevice === d.id ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'
                    }`}
                    activeOpacity={0.7}
                  >
                    <Text className={`text-xs font-semibold ${selectedDevice === d.id ? 'text-white' : 'text-text-secondary'}`}>
                      {d.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </ScrollView>

            {/* Acción */}
            <Text className="text-text text-sm font-semibold mb-2">Acción</Text>
            <View className="flex-row flex-wrap gap-2 mb-5">
              {availableActions.map((a) => (
                <TouchableOpacity
                  key={a.value}
                  onPress={() => setSelectedAction(a.value)}
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${
                    selectedAction === a.value ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'
                  }`}
                  activeOpacity={0.7}
                >
                  <Ionicons name={a.icon as any} size={14} color={selectedAction === a.value ? 'white' : '#94a3b8'} />
                  <Text className={`text-xs font-semibold ${selectedAction === a.value ? 'text-white' : 'text-text-secondary'}`}>
                    {a.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {selectedAction === 'brillo' && (
              <View className="mb-5 flex-row items-center gap-3">
                <Text className="text-text text-sm font-semibold">Brillo:</Text>
                <TouchableOpacity onPress={() => setBrightnessVal(Math.max(0, brightnessVal - 10))}
                  className="w-8 h-8 bg-bg rounded-lg items-center justify-center" activeOpacity={0.7}>
                  <Ionicons name="remove" size={14} color="white" />
                </TouchableOpacity>
                <Text className="text-text font-bold text-base w-12 text-center">{brightnessVal}%</Text>
                <TouchableOpacity onPress={() => setBrightnessVal(Math.min(100, brightnessVal + 10))}
                  className="w-8 h-8 bg-bg rounded-lg items-center justify-center" activeOpacity={0.7}>
                  <Ionicons name="add" size={14} color="white" />
                </TouchableOpacity>
              </View>
            )}

            {/* Frecuencia */}
            <Text className="text-text text-sm font-semibold mb-2">Frecuencia</Text>
            <View className="flex-row flex-wrap gap-2 mb-5">
              {FREQ_OPTIONS.map((f) => (
                <TouchableOpacity
                  key={f.value}
                  onPress={() => setFrequency(f.value)}
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${
                    frequency === f.value ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'
                  }`}
                  activeOpacity={0.7}
                >
                  <Ionicons name={f.icon as any} size={14} color={frequency === f.value ? 'white' : '#94a3b8'} />
                  <Text className={`text-xs font-semibold ${frequency === f.value ? 'text-white' : 'text-text-secondary'}`}>
                    {f.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Fecha — solo para "una vez" */}
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

            {/* Hora */}
            <View className="mb-6">
              <Text className="text-text text-sm font-semibold mb-2">Hora</Text>
              <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3">
                <Ionicons name="time-outline" size={18} color="#6366f1" />
                {/* @ts-ignore */}
                <input type="time" value={timeStr} onChange={(e) => setTimeStr(e.target.value)} disabled={saving}
                  style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
              </View>
            </View>

          </ScrollView>

          {/* Botones */}
          <View className="flex-row gap-3 px-5 pt-2">
            <TouchableOpacity
              className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
              onPress={onClose}
              disabled={saving}
              activeOpacity={0.7}
            >
              <Text className="text-text font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${
                !selectedDevice || saving ? 'bg-indigo-500/40' : 'bg-indigo-500'
              }`}
              onPress={handleConfirm}
              disabled={!selectedDevice || saving}
              activeOpacity={0.8}
            >
              {saving
                ? <ActivityIndicator color="white" size="small" />
                : <Ionicons name="checkmark" size={16} color="white" />
              }
              <Text className="text-text font-semibold text-sm">
                {saving ? 'Guardando...' : 'Crear tarea'}
              </Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>

    </Modal>
  );
}
