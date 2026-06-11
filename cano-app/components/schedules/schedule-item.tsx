import { View, Text, TouchableOpacity, Switch } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type ScheduleDto } from '@/api/schedules';
import { type HouseMemberRole } from '@/api/houses';
import { labelForAction } from '@/utils/action-labels';

interface ScheduleItemProps {
  schedule: ScheduleDto;
  currentUserId?: string;
  currentUserRole?: HouseMemberRole | null;
  creatorUsername?: string | null;
  onToggle: (id: string, active: boolean) => void;
  onDelete: (id: string, name: string) => void;
}

const ACTION_ICONS: Record<string, string> = {
  encender:          'power',
  apagar:            'power-outline',
  brillo:            'contrast',
  temperatura_color: 'thermometer-outline',
  subir_volumen:     'volume-high',
  bajar_volumen:     'volume-low',
  mute:              'volume-mute',
  set_volumen:       'options-outline',
  abrir_app:         'apps-outline',
  color_rgb:         'color-palette-outline',
};

function cronLabel(cron: string): string {
  const parts = cron.split(' ');
  if (parts.length !== 5) return cron;
  const [mm, hh, , , dow] = parts;
  const time = `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
  if (dow === '*')          return `Cada día a las ${time}`;
  if (dow === '1-5')        return `Días laborables ${time}`;
  if (dow === '0,6' || dow === '6,0') return `Fines de semana ${time}`;
  return `${cron} (${time})`;
}

function scheduleTimeLabel(schedule: ScheduleDto): string {
  if (schedule.cron_expr) return cronLabel(schedule.cron_expr);
  const d = new Date(schedule.next_run_at);
  return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' });
}

function getStatusColor(lastCmd: ScheduleDto['last_command']): string {
  if (!lastCmd) return '#94a3b8';
  return lastCmd.status === 'executed' ? '#22c55e' : '#ef4444';
}

function getStatusLabel(lastCmd: ScheduleDto['last_command']): string {
  if (!lastCmd) return 'Sin ejecutar';
  return lastCmd.status === 'executed' ? 'OK' : 'Error';
}

function getContainerStyle(isForeign: boolean, isActive: boolean): string {
  if (isForeign) return 'bg-bg border-amber-500/20';
  if (isActive) return 'bg-bg-secondary border-border';
  return 'bg-bg border-border/50';
}

function getTitleColor(isActive: boolean, isForeign: boolean): string {
  if (!isActive) return 'text-text-secondary';
  return isForeign ? 'text-text/70' : 'text-text';
}

interface RightActionProps {
  isCompleted: boolean;
  isForeign:   boolean;
  schedule:    ScheduleDto;
  onToggle:    (id: string, active: boolean) => void;
}

function RightAction({ isCompleted, isForeign, schedule, onToggle }: Readonly<RightActionProps>) {
  if (isCompleted) {
    return (
      <View className="bg-bg px-2 py-0.5 rounded-full">
        <Text className="text-text-secondary text-xs font-semibold">Completada</Text>
      </View>
    );
  }
  if (isForeign) {
    return (
      <View className="w-8 h-8 items-center justify-center">
        <Ionicons name="lock-closed-outline" size={15} color="#f59e0b" />
      </View>
    );
  }
  return (
    <Switch
      value={schedule.is_active}
      onValueChange={(v) => onToggle(schedule.id, v)}
      trackColor={{ false: '#334155', true: '#3B82F6' }}
      thumbColor="white"
      style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
    />
  );
}

export function ScheduleItem({
  schedule,
  currentUserId,
  currentUserRole,
  creatorUsername,
  onToggle,
  onDelete,
}: Readonly<ScheduleItemProps>) {
  const actionLabel = labelForAction(schedule.action);
  const actionIcon  = ACTION_ICONS[schedule.action]  ?? 'flash';
  const deviceName  = schedule.devices?.name ?? 'Dispositivo';
  const timeLabel   = scheduleTimeLabel(schedule);

  const isOwn       = currentUserId ? schedule.user_id === currentUserId : true;
  const isOwner     = currentUserRole === 'owner';
  const canDelete   = isOwn || isOwner;
  const isForeign   = !isOwn && !isOwner;
  const isCompleted = !schedule.cron_expr && !schedule.is_active;

  const lastCmd     = schedule.last_command;
  const statusColor = getStatusColor(lastCmd);
  const statusLabel = getStatusLabel(lastCmd);

  return (
    <View className={`border rounded-xl px-4 py-3 mb-3 ${getContainerStyle(isForeign, schedule.is_active)}`}>
      {/* Header row */}
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-row items-center gap-2 flex-1">
          <View className={`w-8 h-8 rounded-lg items-center justify-center ${isForeign ? 'bg-amber-500/10' : 'bg-primary/10'}`}>
            <Ionicons name={actionIcon as any} size={16} color={isForeign ? '#f59e0b' : '#3B82F6'} />
          </View>
          <View className="flex-1">
            <View className="flex-row items-center gap-2 flex-wrap">
              <Text
                className={`font-semibold text-sm ${getTitleColor(schedule.is_active, isForeign)}`}
                numberOfLines={1}
              >
                {schedule.name}
              </Text>
              {!isOwn && (
                <View className={`rounded-full px-2 py-0.5 ${isForeign ? 'bg-amber-500/15' : 'bg-bg'}`}>
                  <Text className={`text-xs ${isForeign ? 'text-amber-400' : 'text-text-secondary'}`}>
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

        {canDelete ? (
          <TouchableOpacity
            onPress={() => onDelete(schedule.id, schedule.name)}
            className="w-8 h-8 items-center justify-center"
            activeOpacity={0.7}
          >
            <Ionicons name="trash-outline" size={16} color="#ef4444" />
          </TouchableOpacity>
        ) : (
          <View className="w-8 h-8" />
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
          <View className="flex-row items-center gap-1">
            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: statusColor }} />
            <Text className="text-xs" style={{ color: statusColor }}>{statusLabel}</Text>
          </View>

          <RightAction
            isCompleted={isCompleted}
            isForeign={isForeign}
            schedule={schedule}
            onToggle={onToggle}
          />
        </View>
      </View>
    </View>
  );
}
