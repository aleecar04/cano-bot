import React, { useState } from 'react';
import {
  View, TouchableOpacity, Dimensions, Text, ActivityIndicator,
  Modal, TextInput, ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { roomSchedule, floorSchedule, type SchedulePayload } from '@/api/houses';
import { friendlyError } from '@/utils/friendly-error';

const USER_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

type Frequency = 'once' | 'daily' | 'weekdays' | 'weekends';

const FREQ_OPTIONS: { value: Frequency; label: string; icon: string }[] = [
  { value: 'once',     label: 'Una vez',        icon: 'calendar-outline' },
  { value: 'daily',    label: 'Cada día',        icon: 'repeat' },
  { value: 'weekdays', label: 'Días laborables', icon: 'briefcase-outline' },
  { value: 'weekends', label: 'Fin de semana',   icon: 'sunny-outline' },
];

function buildCron(freq: Frequency, date: Date): string {
  const h = date.getHours(), m = date.getMinutes();
  if (freq === 'daily')    return `${m} ${h} * * *`;
  if (freq === 'weekdays') return `${m} ${h} * * 1-5`;
  if (freq === 'weekends') return `${m} ${h} * * 0,6`;
  return '';
}

function toDateStr(d: Date): string {
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
}
function toTimeStr(d: Date): string { return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; }

interface Room {
  id: string;
  name: string;
  order: number;
  type?: string;
}

interface RoomGridProps {
  floorId: string;
  floorName: string;
  rooms: Room[];
  onRoomPress?: (room: Room) => void;
  onAddRoom?: () => void;
  onDeleteFloor?: (floorId: string, floorName: string) => void;
  onDeleteRoom?: (floorId: string, roomId: string, roomName: string) => void;
  // Group action callbacks
  onFloorAction?: (floorId: string, action: 'encender' | 'apagar') => void;
  // Loading states: set of IDs currently executing
  floorLoadingId?: string | null;
  // Toast callback
  onToast?: (message: string, variant: 'success' | 'error') => void;
}

const getIconForRoom = (roomName: string): string => {
  const name = roomName.toLowerCase();
  if (name.includes('cocina')) return 'restaurant';
  if (name.includes('salon') || name.includes('salón')) return 'tv';
  if (name.includes('dormitorio') || name.includes('cuarto')) return 'bed';
  if (name.includes('baño')) return 'water';
  if (name.includes('oficina')) return 'briefcase';
  if (name.includes('comedor')) return 'restaurant-outline';
  if (name.includes('terraza') || name.includes('jardín')) return 'leaf';
  return 'home-outline';
};

// ── Schedule Modal ─────────────────────────────────────────────────────────────

export type ScheduleTarget =
  | { kind: 'room'; id: string; name: string }
  | { kind: 'floor'; id: string; name: string };

interface ScheduleModalProps {
  visible: boolean;
  target: ScheduleTarget | null;
  onClose: () => void;
  onToast?: (message: string, variant: 'success' | 'error') => void;
}

export const GroupScheduleModal: React.FC<ScheduleModalProps> = ({ visible, target, onClose, onToast }) => {
  const [action, setAction]         = useState<'encender' | 'apagar'>('encender');
  const [freq, setFreq]             = useState<Frequency>('daily');
  const [dateStr, setDateStr]       = useState(toDateStr(new Date()));
  const [timeStr, setTimeStr]       = useState(toTimeStr(new Date()));
  const [name, setName]             = useState('');
  const [submitting, setSubmitting] = useState(false);

  React.useEffect(() => {
    if (!visible || !target) return;
    const verb = action === 'encender' ? 'Encender' : 'Apagar';
    setName(`${verb} ${target.name}`);
    const now = new Date();
    setDateStr(toDateStr(now));
    setTimeStr(toTimeStr(now));
  }, [visible, action, target]);

  const handleSubmit = async () => {
    if (!target) return;
    const taskName = name.trim() || `${action} ${target.name}`;
    const isRecurring = freq !== 'once';
    const dt = new Date(`${dateStr}T${timeStr}:00`);
    const payload: SchedulePayload = {
      name: taskName, action,
      timezone: USER_TZ,
      ...(isRecurring ? { cron_expr: buildCron(freq, dt) } : { run_at: dt.toISOString() }),
    };
    setSubmitting(true);
    try {
      const result = target.kind === 'room'
        ? await roomSchedule(target.id, payload)
        : await floorSchedule(target.id, payload);
      onToast?.(`Tarea programada para ${result.created} dispositivo${result.created !== 1 ? 's' : ''}`, 'success');
      onClose();
    } catch (err) {
      onToast?.(friendlyError(err), 'error');
    } finally {
      setSubmitting(false);
    }
  };

  if (!target) return null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={() => { if (!submitting) onClose(); }}>
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary rounded-t-3xl border-t border-border pb-8">

          {/* Header */}
          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <View>
              <Text className="text-text text-base font-bold">Programar acción</Text>
              <Text className="text-text-secondary text-xs mt-0.5" numberOfLines={1}>{target.name}</Text>
            </View>
            <TouchableOpacity onPress={onClose} disabled={submitting} activeOpacity={0.7}>
              <Ionicons name="close" size={22} color="#94a3b8" />
            </TouchableOpacity>
          </View>

          <ScrollView className="px-5 pt-4" showsVerticalScrollIndicator={false} style={{ maxHeight: 480 }}>

            {/* Nombre */}
            <Text className="text-text text-sm font-semibold mb-2">Nombre (opcional)</Text>
            <TextInput
              className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm mb-5"
              value={name} onChangeText={setName}
              placeholder="Ej. Encender salón" placeholderTextColor="#64748b"
              editable={!submitting}
            />

            {/* Acción */}
            <Text className="text-text text-sm font-semibold mb-2">Acción</Text>
            <View className="flex-row gap-2 mb-5">
              {(['encender', 'apagar'] as const).map((a) => (
                <TouchableOpacity key={a} onPress={() => setAction(a)} activeOpacity={0.7}
                  className={`flex-1 flex-row items-center justify-center gap-1.5 px-3 py-2 rounded-lg border ${action === a ? (a === 'encender' ? 'bg-green-500/20 border-green-500/50' : 'bg-red-500/20 border-red-500/50') : 'bg-bg border-border'}`}>
                  <Ionicons name={a === 'encender' ? 'power' : 'power-outline'} size={14} color={action === a ? (a === 'encender' ? '#4ade80' : '#f87171') : '#94a3b8'} />
                  <Text className={`text-xs font-semibold ${action === a ? (a === 'encender' ? 'text-green-400' : 'text-red-400') : 'text-text-secondary'}`}>
                    {a === 'encender' ? 'Encender' : 'Apagar'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Frecuencia */}
            <Text className="text-text text-sm font-semibold mb-2">Frecuencia</Text>
            <View className="flex-row flex-wrap gap-2 mb-5">
              {FREQ_OPTIONS.map((f) => (
                <TouchableOpacity key={f.value} onPress={() => setFreq(f.value)} activeOpacity={0.7}
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${freq === f.value ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                  <Ionicons name={f.icon as any} size={13} color={freq === f.value ? 'white' : '#94a3b8'} />
                  <Text className={`text-xs font-semibold ${freq === f.value ? 'text-white' : 'text-text-secondary'}`}>{f.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Fecha — solo "Una vez" */}
            {freq === 'once' && (
              <View className="mb-4">
                <Text className="text-text text-sm font-semibold mb-2">Fecha</Text>
                <View className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3">
                  <Ionicons name="calendar-outline" size={18} color="#6366f1" />
                  {/* @ts-ignore */}
                  <input type="date" value={dateStr} onChange={(e) => setDateStr(e.target.value)} disabled={submitting}
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
                <input type="time" value={timeStr} onChange={(e) => setTimeStr(e.target.value)} disabled={submitting}
                  style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: '14px', fontWeight: '600', flex: 1, outline: 'none' }} />
              </View>
            </View>

          </ScrollView>

          {/* Botones */}
          <View className="flex-row gap-3 px-5 pt-2">
            <TouchableOpacity className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
              onPress={onClose} disabled={submitting} activeOpacity={0.7}>
              <Text className="text-text font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${submitting ? 'bg-indigo-500/40' : 'bg-indigo-500'}`}
              onPress={handleSubmit} disabled={submitting} activeOpacity={0.8}>
              {submitting ? <ActivityIndicator color="white" size="small" /> : <Ionicons name="checkmark" size={16} color="white" />}
              <Text className="text-text font-semibold text-sm">{submitting ? 'Guardando...' : 'Programar'}</Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>

    </Modal>
  );
};

// ── ActionButtons ──────────────────────────────────────────────────────────────

/** Encender / Apagar / Programar pill buttons used on floor header and room cards. */
const ActionButtons: React.FC<{
  loading: boolean;
  onEncender: () => void;
  onApagar: () => void;
  onSchedule: () => void;
  compact?: boolean;
}> = ({ loading, onEncender, onApagar, onSchedule, compact = false }) => {
  if (loading) {
    return <ActivityIndicator size="small" color="#3B82F6" style={{ marginHorizontal: 4 }} />;
  }

  if (compact) {
    // Compact layout for room cards (no text label on Encender/Apagar, only icons)
    return (
      <View className="flex-row gap-1 justify-center">
        <TouchableOpacity
          className="bg-green-500/15 border border-green-500/30 rounded-full px-2 py-1 flex-row items-center gap-1"
          onPress={onEncender}
          activeOpacity={0.7}
        >
          <Ionicons name="power" size={11} color="#22c55e" />
          <Text className="text-green-400 text-xs font-semibold">On</Text>
        </TouchableOpacity>
        <TouchableOpacity
          className="bg-red-500/15 border border-red-500/30 rounded-full px-2 py-1 flex-row items-center gap-1"
          onPress={onApagar}
          activeOpacity={0.7}
        >
          <Ionicons name="power-outline" size={11} color="#ef4444" />
          <Text className="text-red-400 text-xs font-semibold">Off</Text>
        </TouchableOpacity>
        <TouchableOpacity
          className="bg-bg/60 border border-border/40 rounded-full px-2 py-1 flex-row items-center gap-1"
          onPress={onSchedule}
          activeOpacity={0.7}
        >
          <Ionicons name="time-outline" size={11} color="#94a3b8" />
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View className="flex-row gap-1">
      <TouchableOpacity
        className="bg-green-500/15 border border-green-500/30 rounded-full px-3 py-1 flex-row items-center gap-1"
        onPress={onEncender}
        activeOpacity={0.7}
      >
        <Ionicons name="power" size={13} color="#22c55e" />
        <Text className="text-green-400 text-xs font-semibold">Encender</Text>
      </TouchableOpacity>
      <TouchableOpacity
        className="bg-red-500/15 border border-red-500/30 rounded-full px-3 py-1 flex-row items-center gap-1"
        onPress={onApagar}
        activeOpacity={0.7}
      >
        <Ionicons name="power-outline" size={13} color="#ef4444" />
        <Text className="text-red-400 text-xs font-semibold">Apagar</Text>
      </TouchableOpacity>
      <TouchableOpacity
        className="bg-bg/60 border border-border/40 rounded-full px-3 py-1 flex-row items-center gap-1"
        onPress={onSchedule}
        activeOpacity={0.7}
      >
        <Ionicons name="time-outline" size={13} color="#94a3b8" />
        <Text className="text-text-secondary text-xs font-semibold">Programar</Text>
      </TouchableOpacity>
    </View>
  );
};

// ── RoomGrid ───────────────────────────────────────────────────────────────────

export const RoomGrid: React.FC<RoomGridProps> = ({
  floorId, floorName, rooms, onRoomPress, onAddRoom, onDeleteFloor, onDeleteRoom,
  onFloorAction, floorLoadingId, onToast,
}) => {
  const screenWidth = Dimensions.get('window').width;
  const GAP = 8;
  const sidepadding = 32 + 16 + (GAP * 2) + 4;
  const roomSize = Math.floor((screenWidth - sidepadding) / 3);

  const floorLoading = floorLoadingId === floorId;

  const [scheduleTarget, setScheduleTarget] = useState<ScheduleTarget | null>(null);

  return (
    <View className="mb-4 bg-bg-secondary rounded-xl p-3 border border-border">
      {/* Floor header */}
      <View className="flex-row justify-between items-center mb-3 flex-wrap gap-y-2">
        <Text className="text-text text-base font-semibold flex-shrink mr-2">{floorName}</Text>
        <View className="flex-row gap-2 items-center flex-shrink-0">
          {onFloorAction && (
            <ActionButtons
              loading={floorLoading}
              onEncender={() => onFloorAction(floorId, 'encender')}
              onApagar={() => onFloorAction(floorId, 'apagar')}
              onSchedule={() => setScheduleTarget({ kind: 'floor', id: floorId, name: floorName })}
            />
          )}
          {onAddRoom && (
            <TouchableOpacity onPress={onAddRoom} activeOpacity={0.7}>
              <Ionicons name="add-circle" size={22} color="#3B82F6" />
            </TouchableOpacity>
          )}
          {onDeleteFloor && (
            <TouchableOpacity onPress={() => onDeleteFloor(floorId, floorName)} activeOpacity={0.7}>
              <Ionicons name="trash-outline" size={18} color="#ef4444" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {rooms.length === 0 ? (
        <Text className="text-text-secondary text-xs text-center py-3">
          Sin habitaciones — pulsa + para añadir una
        </Text>
      ) : (
        <View className="flex-row flex-wrap" style={{ gap: GAP }}>
          {rooms.map((room) => {
            return (
              <View key={room.id} style={{ width: roomSize }}>
                <TouchableOpacity
                  style={{ height: roomSize }}
                  className="bg-bg rounded-lg justify-center items-center border border-border shadow-sm"
                  onPress={() => onRoomPress?.(room)}
                  activeOpacity={0.7}
                >
                  <Ionicons name={getIconForRoom(room.name) as any} size={18} color="#3B82F6" />
                  <Text numberOfLines={1} className="text-xs font-medium text-center text-text mt-1 px-1">
                    {room.name}
                  </Text>
                </TouchableOpacity>

                {onDeleteRoom && (
                  <TouchableOpacity
                    className="absolute top-0.5 right-0.5 w-5 h-5 bg-red-500/80 rounded-full items-center justify-center"
                    onPress={() => onDeleteRoom(floorId, room.id, room.name)}
                    activeOpacity={0.7}
                  >
                    <Ionicons name="close" size={10} color="white" />
                  </TouchableOpacity>
                )}
              </View>
            );
          })}
        </View>
      )}

      {/* Schedule modal is scoped per RoomGrid to avoid prop-drilling */}
      <GroupScheduleModal
        visible={scheduleTarget !== null}
        target={scheduleTarget}
        onClose={() => setScheduleTarget(null)}
        onToast={onToast}
      />
    </View>
  );
};
