import { useCallback, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from 'expo-router';
import { getDevices, waitForCommand, type DeviceDto } from '@/api/devices';
import {
  getFavorites, addFavorite, deleteFavorite, executeFavorite,
  type FavoriteDto, type AddFavoriteParams,
} from '@/api/favorites';
import { friendlyError } from '@/utils/friendly-error';
import { Toast } from '@/components/ui/toast';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { AddFavoriteModal } from '@/components/ui/add-favorite-modal';
import { deviceIcon } from '@/utils/device-icons';
import { useUserProfile } from '@/context/user-profile';

// ── Helpers ───────────────────────────────────────────────────────────────────

const ACTION_ICONS: Record<string, string> = {
  encender:      'power',
  apagar:        'power-outline',
  brillo:        'sunny',
  subir_volumen: 'volume-high',
  bajar_volumen: 'volume-low',
  mute:          'volume-mute',
};

const ACTION_COLORS = ['#6366f1', '#3B82F6', '#10b981', '#f59e0b'];

const ACCIONES_POR_TIPO: Record<string, { accion: string; icon: string; label: string }[]> = {
  SmartTV: [
    { accion: 'encender',      icon: 'power',         label: 'Encender' },
    { accion: 'apagar',        icon: 'power-outline', label: 'Apagar' },
    { accion: 'subir_volumen', icon: 'volume-high',   label: 'Vol +' },
    { accion: 'bajar_volumen', icon: 'volume-low',    label: 'Vol -' },
    { accion: 'mute',          icon: 'volume-mute',   label: 'Mute' },
  ],
  Luz: [
    { accion: 'encender', icon: 'sunny',        label: 'Encender' },
    { accion: 'apagar',   icon: 'moon-outline', label: 'Apagar' },
    { accion: 'brillo',   icon: 'contrast',     label: 'Brillo' },
  ],
  Termostato: [
    { accion: 'encender', icon: 'power',         label: 'Encender' },
    { accion: 'apagar',   icon: 'power-outline', label: 'Apagar' },
  ],
  IoT: [
    { accion: 'encender', icon: 'power',         label: 'Encender' },
    { accion: 'apagar',   icon: 'power-outline', label: 'Apagar' },
  ],
  light: [
    { accion: 'encender', icon: 'sunny',        label: 'Encender' },
    { accion: 'apagar',   icon: 'moon-outline', label: 'Apagar' },
    { accion: 'brillo',   icon: 'contrast',     label: 'Brillo' },
  ],
  switch: [
    { accion: 'encender', icon: 'power',         label: 'Encender' },
    { accion: 'apagar',   icon: 'power-outline', label: 'Apagar' },
  ],
  climate: [
    { accion: 'encender', icon: 'power',         label: 'Encender' },
    { accion: 'apagar',   icon: 'power-outline', label: 'Apagar' },
  ],
  cover: [
    { accion: 'encender', icon: 'arrow-up',   label: 'Abrir' },
    { accion: 'apagar',   icon: 'arrow-down', label: 'Cerrar' },
  ],
  media_player: [
    { accion: 'encender',      icon: 'play',        label: 'Play' },
    { accion: 'apagar',        icon: 'pause',       label: 'Pausa' },
    { accion: 'subir_volumen', icon: 'volume-high', label: 'Vol +' },
    { accion: 'bajar_volumen', icon: 'volume-low',  label: 'Vol -' },
    { accion: 'mute',          icon: 'volume-mute', label: 'Mute' },
  ],
};

const DEFAULT_ACCIONES = [
  { accion: 'encender', icon: 'power',         label: 'Encender' },
  { accion: 'apagar',   icon: 'power-outline', label: 'Apagar' },
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 13) return 'Buenos días';
  if (h < 21) return 'Buenas tardes';
  return 'Buenas noches';
}

function favoriteLabel(fav: FavoriteDto): string {
  if (fav.label) return fav.label;
  const action = ACTION_ICONS[fav.action] ? fav.action.replace('_', ' ') : fav.action;
  return `${action} ${fav.devices?.name ?? ''}`.trim();
}

// ── Component ────────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const { profile } = useUserProfile();
  const [favorites, setFavorites]   = useState<FavoriteDto[]>([]);
  const [devices, setDevices]       = useState<DeviceDto[]>([]);
  const [loading, setLoading]       = useState(true);
  const [toast, setToast]           = useState<{ message: string; variant: 'success' | 'error' } | null>(null);
  const [runningId, setRunningId]   = useState<string | null>(null);

  const [showAddModal, setShowAddModal]     = useState(false);
  const [addStep, setAddStep]               = useState<'device' | 'action'>('device');
  const [pendingDevice, setPendingDevice]   = useState<DeviceDto | null>(null);
  const [savingFavorite, setSavingFavorite] = useState(false);
  const [removeTarget, setRemoveTarget]     = useState<FavoriteDto | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [favData, devData] = await Promise.all([getFavorites(), getDevices()]);
      setFavorites(favData);
      setDevices(devData);
    } catch {
      // silent — empty state shown
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const handleRunFavorite = async (fav: FavoriteDto) => {
    setRunningId(fav.id);
    try {
      const { command_id } = await executeFavorite(fav.id);
      const cmd = await waitForCommand(command_id);
      if (cmd.status === 'failed') {
        setToast({ message: cmd.error || 'Error ejecutando comando', variant: 'error' });
      } else {
        setToast({ message: `${favoriteLabel(fav)} ejecutado`, variant: 'success' });
        // Refresh device list so is_online / estado reflect updated state
        const devData = await getDevices();
        setDevices(devData);
      }
    } catch (err) {
      const msg = String(err).includes('timeout')
        ? 'El dispositivo no respondió a tiempo'
        : friendlyError(err);
      setToast({ message: msg, variant: 'error' });
    } finally {
      setRunningId(null);
    }
  };

  const handleSelectDevice = (device: DeviceDto) => {
    setPendingDevice(device);
    setAddStep('action');
  };

  const handleSelectAction = async (accion: string, label: string) => {
    if (!pendingDevice) return;
    setSavingFavorite(true);
    try {
      const created = await addFavorite({
        device_id: pendingDevice.id,
        action:    accion,
        label:     `${label} ${pendingDevice.name}`,
      } as AddFavoriteParams);
      setFavorites((prev) => [...prev, created]);
      setShowAddModal(false);
      setToast({ message: 'Añadido a acciones rápidas', variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setSavingFavorite(false);
      setPendingDevice(null);
      setAddStep('device');
    }
  };

  const closeAddModal = () => {
    setShowAddModal(false);
    setPendingDevice(null);
    setAddStep('device');
  };

  const handleConfirmRemove = async () => {
    if (!removeTarget) return;
    const target = removeTarget;
    setRemoveTarget(null);
    try {
      await deleteFavorite(target.id);
      setFavorites((prev) => prev.filter((f) => f.id !== target.id));
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    }
  };

  if (loading) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <ActivityIndicator size="large" color="#3B82F6" />
      </SafeAreaView>
    );
  }

  const firstName = profile?.first_name || profile?.username || '';
  const actionItems = ACCIONES_POR_TIPO[pendingDevice?.type ?? ''] ?? DEFAULT_ACCIONES;
  const canAddMore  = favorites.length < 4;
  const onlineCount = devices.filter((d) => d.is_online).length;

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>

        {/* Greeting */}
        <View className="px-5 pt-5 pb-4">
          <Text className="text-text-secondary text-sm font-medium">{greeting()}</Text>
          <Text className="text-text text-2xl font-black mt-0.5">
            {firstName ? firstName : 'Inicio'}
          </Text>
        </View>

        {/* Stats strip */}
        {devices.length > 0 && (
          <View className="flex-row gap-3 px-5 mb-6">
            <View className="flex-1 bg-bg-secondary border border-border rounded-xl px-3 py-3 items-start gap-1">
              <Ionicons name="hardware-chip-outline" size={16} color="#64748b" />
              <Text className="text-text font-bold text-xl">{devices.length}</Text>
              <Text className="text-text-secondary text-xs">Dispositivos</Text>
            </View>
            <View className="flex-1 bg-bg-secondary border border-border rounded-xl px-3 py-3 items-start gap-1">
              <View className="flex-row items-center gap-1.5">
                <Ionicons name="wifi" size={16} color={onlineCount > 0 ? '#10b981' : '#64748b'} />
                {onlineCount > 0 && <View className="w-1.5 h-1.5 rounded-full bg-green-500" />}
              </View>
              <Text className="text-text font-bold text-xl">{onlineCount}</Text>
              <Text className="text-text-secondary text-xs">En línea</Text>
            </View>
            <View className="flex-1 bg-bg-secondary border border-border rounded-xl px-3 py-3 items-start gap-1">
              <Ionicons name="star-outline" size={16} color="#64748b" />
              <Text className="text-text font-bold text-xl">{favorites.length}</Text>
              <Text className="text-text-secondary text-xs">Favoritos</Text>
            </View>
          </View>
        )}

        {/* Quick actions */}
        <View className="px-5 mb-6">
          <View className="flex-row items-center justify-between mb-3">
            <Text className="text-text font-bold text-base">Acciones rápidas</Text>
            {canAddMore && (
              <TouchableOpacity onPress={() => setShowAddModal(true)} activeOpacity={0.7}>
                <Text className="text-primary text-sm font-semibold">+ Añadir</Text>
              </TouchableOpacity>
            )}
          </View>

          {favorites.length === 0 ? (
            <TouchableOpacity
              onPress={() => setShowAddModal(true)}
              className="bg-bg-secondary border border-dashed border-border rounded-2xl py-8 items-center"
              activeOpacity={0.7}
            >
              <View className="w-12 h-12 rounded-full bg-primary/10 items-center justify-center mb-3">
                <Ionicons name="add" size={24} color="#3B82F6" />
              </View>
              <Text className="text-text font-semibold text-sm">Añadir acción rápida</Text>
              <Text className="text-text-secondary text-xs mt-1">Fija tus controles favoritos aquí</Text>
            </TouchableOpacity>
          ) : (
            <View className="flex-row flex-wrap gap-3">
              {favorites.map((fav, idx) => {
                const color   = ACTION_COLORS[idx % ACTION_COLORS.length];
                const icon    = ACTION_ICONS[fav.action] ?? 'flash';
                const label   = favoriteLabel(fav);
                const running = runningId === fav.id;

                return (
                  <TouchableOpacity
                    key={fav.id}
                    style={{ width: '47%' }}
                    className="bg-bg-secondary rounded-2xl p-4 border border-border"
                    onPress={() => handleRunFavorite(fav)}
                    onLongPress={() => setRemoveTarget(fav)}
                    activeOpacity={0.75}
                  >
                    <View
                      className="w-10 h-10 rounded-xl items-center justify-center mb-3"
                      style={{ backgroundColor: `${color}20` }}
                    >
                      {running
                        ? <ActivityIndicator color={color} size="small" />
                        : <Ionicons name={icon as any} size={22} color={color} />
                      }
                    </View>
                    <Text className="text-text text-sm font-bold" numberOfLines={1}>{label}</Text>
                    <Text className="text-text-secondary text-xs mt-0.5" numberOfLines={1}>
                      {fav.devices?.name ?? ''}
                    </Text>
                  </TouchableOpacity>
                );
              })}

              {canAddMore && (
                <TouchableOpacity
                  style={{ width: '47%' }}
                  className="bg-bg-secondary rounded-2xl p-4 border border-dashed border-border items-center justify-center min-h-[110px]"
                  onPress={() => setShowAddModal(true)}
                  activeOpacity={0.7}
                >
                  <Ionicons name="add-circle-outline" size={28} color="#475569" />
                  <Text className="text-text-secondary text-xs mt-2">Añadir</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>

        <View className="pb-10" />

      </ScrollView>

      <AddFavoriteModal
        visible={showAddModal}
        devices={devices}
        step={addStep}
        pendingDevice={pendingDevice}
        actionItems={actionItems}
        saving={savingFavorite}
        onClose={closeAddModal}
        onSelectDevice={handleSelectDevice}
        onSelectAction={handleSelectAction}
        onBack={() => setAddStep('device')}
      />

      <ConfirmModal
        visible={removeTarget !== null}
        title="Quitar acción rápida"
        message={`¿Quitar "${removeTarget ? favoriteLabel(removeTarget) : ''}"?`}
        confirmLabel="Quitar"
        destructive
        onConfirm={handleConfirmRemove}
        onCancel={() => setRemoveTarget(null)}
      />

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'success'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </SafeAreaView>
  );
}
