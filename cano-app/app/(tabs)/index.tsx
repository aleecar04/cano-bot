import { useCallback, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from 'expo-router';
import { getDevices, waitForCommand, type DeviceDto } from '@/api/devices';
import {
  getFavorites, addFavorite, deleteFavorite, executeFavorite, updateFavorite,
  type FavoriteDto,
} from '@/api/favorites';
import { friendlyError } from '@/utils/friendly-error';
import { Toast } from '@/components/ui/toast';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { AddFavoriteModal } from '@/components/ui/add-favorite-modal';
import { EditFavoriteModal } from '@/components/ui/edit-favorite-modal';
import {
  getActionsForType, type PayloadType,
  LUZ_COLORES, TEMP_PRESETS, kelvinToHex, TV_APPS,
} from '@/utils/device-actions';
import { useUserProfile } from '@/context/user-profile';

// ── Helpers ───────────────────────────────────────────────────────────────────

const ACTION_ICON_MAP: Record<string, string> = {
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

const ACTION_COLORS = ['#6366f1', '#3B82F6', '#10b981', '#f59e0b'];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 13) return 'Buenos días';
  if (h < 21) return 'Buenas tardes';
  return 'Buenas noches';
}

function favoriteLabel(fav: FavoriteDto): string {
  if (fav.label) return fav.label;
  return `${fav.action.replace('_', ' ')} ${fav.devices?.name ?? ''}`.trim();
}

function favoriteIcon(fav: FavoriteDto): string {
  const type    = fav.devices?.type ?? '';
  const actions = getActionsForType(type);
  return actions.find((a) => a.action === fav.action)?.icon
    ?? ACTION_ICON_MAP[fav.action]
    ?? 'flash';
}

// ── Payload badge ─────────────────────────────────────────────────────────────

function FavPayloadBadge({ fav, payloadType }: Readonly<{ fav: FavoriteDto; payloadType: PayloadType }>) {
  const p = fav.payload ?? {};

  if (payloadType === 'brightness' && typeof p.value === 'number') {
    return (
      <View className="flex-row items-center gap-1.5 mt-2.5">
        <Ionicons name="contrast" size={11} color="#64748b" />
        <View className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
          <View style={{ width: `${p.value}%`, height: '100%', backgroundColor: '#6366f1', borderRadius: 99 }} />
        </View>
        <Text className="text-text-secondary text-xs">{p.value}%</Text>
      </View>
    );
  }

  if (payloadType === 'color_temp' && typeof p.value === 'number') {
    const preset = TEMP_PRESETS.reduce(
      (a, b) =>
        Math.abs(b.value - (p.value as number)) < Math.abs(a.value - (p.value as number)) ? b : a,
      TEMP_PRESETS[0],
    );
    return (
      <View className="flex-row items-center gap-1.5 mt-2.5">
        <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: kelvinToHex(p.value) }} />
        <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: kelvinToHex(p.value), opacity: 0.6 }} />
        <Text className="text-text-secondary text-xs">{preset.label}</Text>
      </View>
    );
  }

  if (payloadType === 'color' && typeof p.color === 'string') {
    const col = LUZ_COLORES.find((c) => c.name === p.color);
    return (
      <View className="flex-row items-center gap-1.5 mt-2.5">
        <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: col?.hex ?? '#ffffff', borderWidth: 1, borderColor: 'rgba(255,255,255,0.3)' }} />
        <View style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: col?.hex ?? '#ffffff', opacity: 0.55 }} />
        <Text className="text-text-secondary text-xs capitalize">{p.color}</Text>
      </View>
    );
  }

  if (payloadType === 'volumen' && typeof p.value === 'number') {
    return (
      <View className="flex-row items-center gap-1.5 mt-2.5">
        <Ionicons name="volume-medium-outline" size={11} color="#64748b" />
        <Text className="text-text-secondary text-xs">Vol {p.value}</Text>
      </View>
    );
  }

  if (payloadType === 'app' && typeof p.app === 'string') {
    const app = TV_APPS.find((a) => a.app === p.app);
    return (
      <View className="flex-row items-center gap-1.5 mt-2.5">
        <Ionicons name={(app?.icon ?? 'apps-outline') as any} size={11} color="#64748b" />
        <Text className="text-text-secondary text-xs">{app?.label ?? p.app}</Text>
      </View>
    );
  }

  return null;
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
  const [savingFavorite, setSavingFavorite] = useState(false);
  const [removeTarget, setRemoveTarget]     = useState<FavoriteDto | null>(null);
  const [editTarget, setEditTarget]         = useState<FavoriteDto | null>(null);
  const [editSaving, setEditSaving]         = useState(false);
  const [menuOpenId, setMenuOpenId]         = useState<string | null>(null);

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

  const handleSelectAction = async (
    device: DeviceDto,
    action: string,
    label: string,
    payload: Record<string, unknown>,
  ) => {
    setSavingFavorite(true);
    try {
      const created = await addFavorite({
        device_id: device.id,
        action,
        label,  // nombre que el usuario ha escrito en el modal
        payload,
      });
      setFavorites((prev) => [...prev, created]);
      setShowAddModal(false);
      setToast({ message: 'Añadido a acciones rápidas', variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setSavingFavorite(false);
    }
  };

  const handleEditFavorite = async (
    id: string,
    action: string,
    payload: Record<string, unknown>,
    label: string,
  ) => {
    setEditSaving(true);
    try {
      const updated = await updateFavorite(id, { action, payload, label });
      setFavorites((prev) => prev.map((f) => (f.id === id ? updated : f)));
      setEditTarget(null);
      setToast({ message: 'Favorito actualizado', variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setEditSaving(false);
    }
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

  const firstName  = profile?.first_name || profile?.username || '';
  const canAddMore = favorites.length < 6;
  const onlineCount = devices.filter((d) => d.is_online).length;

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>

        {/* Greeting */}
        <View className="px-5 pt-5 pb-4">
          <Text className="text-text-secondary text-sm font-medium">{greeting()}</Text>
          <Text className="text-text text-2xl font-black mt-0.5">
            {firstName || 'Inicio'}
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
                const color       = ACTION_COLORS[idx % ACTION_COLORS.length];
                const icon        = favoriteIcon(fav);
                const label       = favoriteLabel(fav);
                const running     = runningId === fav.id;
                const device      = devices.find((d) => d.id === fav.device_id);
                const isTuya      = device?.driver === 'tuya';
                const favActions  = getActionsForType(fav.devices?.type ?? device?.type ?? '', isTuya);
                const payloadType = favActions.find((a) => a.action === fav.action)?.payloadType;

                return (
                  <View
                    key={fav.id}
                    style={{ width: '47%' }}
                    className="bg-bg-secondary rounded-2xl border border-border"
                  >
                    <TouchableOpacity
                      className="p-4"
                      onPress={() => handleRunFavorite(fav)}
                      activeOpacity={0.75}
                    >
                      <View className="flex-row items-start justify-between mb-3">
                        <View
                          className="w-10 h-10 rounded-xl items-center justify-center"
                          style={{ backgroundColor: `${color}20` }}
                        >
                          {running
                            ? <ActivityIndicator color={color} size="small" />
                            : <Ionicons name={icon as any} size={22} color={color} />
                          }
                        </View>
                        <TouchableOpacity
                          onPress={() => setMenuOpenId(fav.id)}
                          hitSlop={{ top: 6, right: 6, bottom: 6, left: 6 }}
                          activeOpacity={0.7}
                        >
                          <Ionicons name="ellipsis-horizontal" size={18} color="#64748b" />
                        </TouchableOpacity>
                      </View>
                      <Text className="text-text text-sm font-bold" numberOfLines={1}>{label}</Text>
                      <Text className="text-text-secondary text-xs mt-0.5" numberOfLines={1}>
                        {fav.devices?.name ?? ''}
                      </Text>
                      {payloadType && <FavPayloadBadge fav={fav} payloadType={payloadType} />}
                    </TouchableOpacity>
                  </View>
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
        saving={savingFavorite}
        onClose={() => setShowAddModal(false)}
        onSelectAction={handleSelectAction}
      />

      <Modal
        visible={menuOpenId !== null}
        transparent
        animationType="slide"
        onRequestClose={() => setMenuOpenId(null)}
      >
        <TouchableOpacity
          style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' }}
          activeOpacity={1}
          onPress={() => setMenuOpenId(null)}
        >
          <TouchableOpacity activeOpacity={1}>
            <View className="bg-bg-secondary rounded-t-3xl border-t border-border px-5 pt-3 pb-10">
              <View className="w-10 h-1 bg-border rounded-full self-center mb-5" />
              <TouchableOpacity
                className="flex-row items-center gap-3 py-4 border-b border-border"
                activeOpacity={0.7}
                onPress={() => {
                  const fav = favorites.find((f) => f.id === menuOpenId) ?? null;
                  setMenuOpenId(null);
                  setEditTarget(fav);
                }}
              >
                <View className="w-9 h-9 rounded-xl bg-indigo-500/20 items-center justify-center">
                  <Ionicons name="pencil-outline" size={18} color="#818cf8" />
                </View>
                <Text className="text-text font-semibold">Editar favorito</Text>
              </TouchableOpacity>
              <TouchableOpacity
                className="flex-row items-center gap-3 py-4"
                activeOpacity={0.7}
                onPress={() => {
                  const fav = favorites.find((f) => f.id === menuOpenId) ?? null;
                  setMenuOpenId(null);
                  setRemoveTarget(fav);
                }}
              >
                <View className="w-9 h-9 rounded-xl bg-red-500/20 items-center justify-center">
                  <Ionicons name="trash-outline" size={18} color="#f87171" />
                </View>
                <Text className="text-red-400 font-semibold">Eliminar</Text>
              </TouchableOpacity>
            </View>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>

      <EditFavoriteModal
        visible={editTarget !== null}
        favorite={editTarget}
        devices={devices}
        saving={editSaving}
        onClose={() => setEditTarget(null)}
        onConfirm={handleEditFavorite}
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
