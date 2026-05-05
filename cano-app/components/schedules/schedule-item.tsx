import { View, Text, TouchableOpacity, Switch } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type ScheduleDto } from '@/api/schedules';
import { type HouseMemberRole } from '@/api/houses';

interface ScheduleItemProps {
  schedule: ScheduleDto;
  currentUserId?: string;
  currentUserRole?: HouseMemberRole | null;
  creatorUsername?: string | null;
  onToggle: (id: string, active: boolean) => void;
  onDelete: (id: string, name: string) => void;
}

const ACTION_LABELS: Record<string, string> = {
  encender:      'Encender',
  apagar:        'Apagar',
  brillo:        'Brillo',
  subir_volumen: 'Subir volumen',
  bajar_volumen: 'Bajar volumen',
  mute:          'Silenciar',
};

const ACTION_ICONS: Record<string, string> = {
  encender:      'power',
  apagar:        'power-outline',
  brillo:        'sunny',
  subir_volumen: 'volume-high',
  bajar_volumen: 'volume-low',
  mute:          'volume-mute',
};

function cronLabel(cron: string): string {
  const parts = cron.split(' ');
  if (parts.length !== 5) return cron;
  const [mm, hh, , , dow] = parts;
  // Cron is stored in local time — display as-is
  const time = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
  if (dow === '*')   return `Cada día a las ${time}`;
  if (dow === '1-5') return `Días laborables ${time}`;
  if (dow === '0,6' || dow === '6,0') return `Fines de semana ${time}`;
  return `${cron} (${time})`;
}

function scheduleTimeLabel(schedule: ScheduleDto): string {
  if (schedule.cron_expr) {
    return cronLabel(schedule.cron_expr);
  }
  // One-time: show the scheduled datetime from next_run_at
  const d = new Date(schedule.next_run_at);
  return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
}

export function ScheduleItem({
  schedule,
  currentUserId,
  currentUserRole,
  creatorUsername,
  onToggle,
  onDelete,
}: ScheduleItemProps) {
  const actionLabel = ACTION_LABELS[schedule.action] ?? schedule.action;
  const actionIcon  = ACTION_ICONS[schedule.action]  ?? 'flash';
  const deviceName  = schedule.devices?.name ?? 'Dispositivo';
  const timeLabel   = scheduleTimeLabel(schedule);

  const isOwn    = currentUserId ? schedule.user_id === currentUserId : true;
  const canDelete = isOwn || currentUserRole === 'owner';

  const lastCmd = schedule.last_command;
  const statusColor = !lastCmd
    ? '#94a3b8'
    : lastCmd.status === 'executed'
    ? '#22c55e'
    : '#ef4444';

  const statusLabel = !lastCmd
    ? 'Sin ejecutar'
    : lastCmd.status === 'executed'
    ? 'OK'
    : 'Error';

  return (
    <View className={`border rounded-xl px-4 py-3 mb-3 ${
      schedule.is_active ? 'bg-bg-secondary border-border' : 'bg-bg border-border/50'
    }`}>
      {/* Header row */}
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-row items-center gap-2 flex-1">
          <View className="w-8 h-8 rounded-lg bg-primary/10 items-center justify-center">
            <Ionicons name={actionIcon as any} size={16} color="#3B82F6" />
          </View>
          <View className="flex-1">
            <View className="flex-row items-center gap-2 flex-wrap">
              <Text className={`font-semibold text-sm ${schedule.is_active ? 'text-text' : 'text-text-secondary'}`} numberOfLines={1}>
                {schedule.name}
              </Text>
              {!isOwn && (
                <View className="bg-bg rounded-full px-2 py-0.5">
                  <Text className="text-text-secondary text-xs">
                    {creatorUsername ?? 'Otro miembro'}
                  </Text>
                </View>
              )}
            </View>
            <Text className="text-text-secondary text-xs" numberOfLines={1}>
              {actionLabel} · {deviceName}
            </Text>
          </View>
        </View>
        {canDelete && (
          <TouchableOpacity
            onPress={() => onDelete(schedule.id, schedule.name)}
            className="w-8 h-8 items-center justify-center"
            activeOpacity={0.7}
          >
            <Ionicons name="trash-outline" size={16} color="#ef4444" />
          </TouchableOpacity>
        )}
      </View>

      {/* Time + status row */}
      <View className="flex-row items-center justify-between">
        <View className="flex-row items-center gap-1.5">
          <Ionicons
            name={schedule.cron_expr ? 'repeat' : 'time-outline'}
            size={13}
            color="#94a3b8"
          />
          <Text className="text-text-secondary text-xs">{timeLabel}</Text>
        </View>

        <View className="flex-row items-center gap-3">
          {/* Last status dot */}
          <View className="flex-row items-center gap-1">
            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: statusColor }} />
            <Text className="text-xs" style={{ color: statusColor }}>{statusLabel}</Text>
          </View>

          {/* Toggle — only allow the owner of the schedule to toggle */}
          {isOwn && (
            <Switch
              value={schedule.is_active}
              onValueChange={(v) => onToggle(schedule.id, v)}
              trackColor={{ false: '#334155', true: '#3B82F6' }}
              thumbColor="white"
              style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
            />
          )}
        </View>
      </View>
    </View>
  );
}
