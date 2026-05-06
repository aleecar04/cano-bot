import { useState } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import {
  createSchedule, deleteSchedule, toggleSchedule, deleteCompletedSchedules,
  type ScheduleDto, type CreateScheduleParams,
} from '@/api/schedules';
import { type DeviceDto } from '@/api/devices';
import { type HouseMemberDto, type HouseMemberRole } from '@/api/houses';
import { friendlyError } from '@/utils/friendly-error';
import { ScheduleItem } from '@/components/schedules/schedule-item';
import { CreateScheduleModal } from '@/components/schedules/create-schedule-modal';
import { ConfirmModal } from '@/components/ui/confirm-modal';

interface Props {
  schedules: ScheduleDto[];
  loadingSchedules: boolean;
  devices: DeviceDto[];
  currentUserId?: string;
  currentUserRole?: HouseMemberRole | null;
  houseMembers?: HouseMemberDto[];
  onSchedulesChange: (updater: (prev: ScheduleDto[]) => ScheduleDto[]) => void;
  onToast: (message: string, variant: 'success' | 'error') => void;
}

export function SchedulesTab({
  schedules,
  loadingSchedules,
  devices,
  currentUserId,
  currentUserRole,
  houseMembers,
  onSchedulesChange,
  onToast,
}: Props) {
  const [showCreate, setShowCreate]       = useState(false);
  const [saving, setSaving]               = useState(false);
  const [cleaning, setCleaning]           = useState(false);
  const [deleteTarget, setDeleteTarget]   = useState<{ id: string; name: string } | null>(null);

  const isOwner = currentUserRole === 'owner';
  const completedCount = schedules.filter((s) =>
    !s.cron_expr && !s.is_active && (isOwner || s.user_id === currentUserId)
  ).length;

  const memberMap = new Map<string, string | null>(
    (houseMembers ?? []).map((m) => [m.user_id, m.username])
  );

  const handleCreate = async (params: CreateScheduleParams) => {
    setSaving(true);
    try {
      const created = await createSchedule(params);
      onSchedulesChange((prev) => [created, ...prev]);
      setShowCreate(false);
      onToast(`Tarea "${created.name}" creada`, 'success');
    } catch (err) {
      onToast(friendlyError(err), 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (id: string, active: boolean) => {
    try {
      const updated = await toggleSchedule(id, active);
      onSchedulesChange((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch (err) {
      onToast(friendlyError(err), 'error');
    }
  };

  const handleCleanCompleted = async () => {
    setCleaning(true);
    try {
      const count = await deleteCompletedSchedules();
      onSchedulesChange((prev) => prev.filter((s) =>
        s.cron_expr || s.is_active || (!isOwner && s.user_id !== currentUserId)
      ));
      onToast(`${count} tarea${count !== 1 ? 's' : ''} completada${count !== 1 ? 's' : ''} eliminada${count !== 1 ? 's' : ''}`, 'success');
    } catch (err) {
      onToast(friendlyError(err), 'error');
    } finally {
      setCleaning(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    const { id, name } = deleteTarget;
    setDeleteTarget(null);
    try {
      await deleteSchedule(id);
      onSchedulesChange((prev) => prev.filter((s) => s.id !== id));
      onToast(`Tarea "${name}" eliminada`, 'success');
    } catch (err) {
      onToast(friendlyError(err), 'error');
    }
  };

  return (
    <>
      <View className="flex-row items-center justify-between mb-4">
        <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider">
          Tareas programadas
        </Text>
        <View className="flex-row items-center gap-2">
          {completedCount > 0 && (
            <TouchableOpacity
              onPress={handleCleanCompleted}
              disabled={cleaning}
              className="flex-row items-center gap-1.5 bg-bg border border-border rounded-lg px-3 py-2"
              activeOpacity={0.8}
            >
              {cleaning
                ? <ActivityIndicator size="small" color="#94a3b8" />
                : <Ionicons name="trash-outline" size={14} color="#94a3b8" />
              }
              <Text className="text-text-secondary text-xs font-semibold">
                Limpiar ({completedCount})
              </Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity
            onPress={() => setShowCreate(true)}
            className="flex-row items-center gap-1.5 bg-primary rounded-lg px-3 py-2"
            activeOpacity={0.8}
          >
            <Ionicons name="add" size={15} color="white" />
            <Text className="text-white text-xs font-semibold">Nueva</Text>
          </TouchableOpacity>
        </View>
      </View>

      {loadingSchedules ? (
        <View className="py-12 items-center">
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      ) : schedules.length > 0 ? (
        schedules.map((s) => (
          <ScheduleItem
            key={s.id}
            schedule={s}
            currentUserId={currentUserId}
            currentUserRole={currentUserRole}
            creatorUsername={memberMap.get(s.user_id) ?? null}
            onToggle={handleToggle}
            onDelete={(id, name) => setDeleteTarget({ id, name })}
          />
        ))
      ) : (
        <View className="py-16 items-center">
          <View className="w-16 h-16 rounded-full bg-bg items-center justify-center mb-4">
            <Ionicons name="alarm-outline" size={32} color="#475569" />
          </View>
          <Text className="text-text font-semibold text-base">Sin tareas</Text>
          <Text className="text-text-secondary text-sm text-center mt-2 px-6">
            Automatiza tus dispositivos creando una tarea programada
          </Text>
        </View>
      )}

      <CreateScheduleModal
        visible={showCreate}
        devices={devices}
        saving={saving}
        onClose={() => setShowCreate(false)}
        onConfirm={handleCreate}
      />

      <ConfirmModal
        visible={deleteTarget !== null}
        title="Eliminar tarea"
        message={`¿Eliminar "${deleteTarget?.name}"?`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
