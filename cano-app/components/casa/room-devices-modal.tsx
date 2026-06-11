import { useState } from 'react';
import { View, Text, Modal, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type DeviceDto } from '@/api/devices';
import { roomAction } from '@/api/houses';
import { LinkedDeviceItem } from '@/components/devices/linked-device-item';
import { friendlyError } from '@/utils/friendly-error';
import { Toast } from '@/components/ui/toast';

interface RoomDevice {
  id: string;
  name: string;
  type: string;
  ip: string;
  is_online: boolean;
  state: Record<string, unknown>;
  room_id?: string | null;
}

interface RoomDevicesModalProps {
  visible: boolean;
  roomId: string;
  roomName: string;
  devices: RoomDevice[];
  onClose: () => void;
  onCommandSuccess?: () => void;
  onDeviceUpdate?: (updated: DeviceDto) => void;
  onEditSuccess?: (updated: DeviceDto) => void;
  onUnlinkDevice?: (deviceId: string, deviceName: string) => void;
  onScheduleRoom?: (roomId: string, roomName: string) => void;
}

export function RoomDevicesModal({
  visible,
  roomId,
  roomName,
  devices,
  onClose,
  onCommandSuccess,
  onDeviceUpdate,
  onEditSuccess,
  onUnlinkDevice,
  onScheduleRoom,
}: Readonly<RoomDevicesModalProps>) {
  const [actionLoading, setActionLoading] = useState<'encender' | 'apagar' | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'error' } | null>(null);

  const handleAction = async (action: 'encender' | 'apagar') => {
    setActionLoading(action);
    try {
      await roomAction(roomId, action);
      const label = action === 'encender' ? 'encendidos' : 'apagados';
      setToast({ message: `Dispositivos ${label}`, variant: 'success' });
      onCommandSuccess?.();
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary border-t border-border rounded-t-3xl" style={{ maxHeight: '80%' }}>

          {/* Header */}
          <View className="px-5 pt-5 pb-4 border-b border-border">
            <View className="flex-row items-center justify-between mb-3">
              <View className="flex-row items-center gap-3">
                <View className="w-8 h-8 rounded-xl bg-primary/10 items-center justify-center">
                  <Ionicons name="home-outline" size={16} color="#3B82F6" />
                </View>
                <Text className="text-text font-bold text-base">{roomName}</Text>
              </View>
              <TouchableOpacity onPress={onClose} activeOpacity={0.7}>
                <Ionicons name="close" size={22} color="#64748b" />
              </TouchableOpacity>
            </View>

            {/* Group action buttons */}
            {devices.length > 0 && (
              <View className="flex-row gap-2">
                <TouchableOpacity
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border flex-1 justify-center ${actionLoading ? 'opacity-50' : ''} bg-green-500/15 border-green-500/30`}
                  onPress={() => handleAction('encender')}
                  disabled={actionLoading !== null}
                  activeOpacity={0.7}
                >
                  {actionLoading === 'encender'
                    ? <ActivityIndicator size="small" color="#4ade80" />
                    : <Ionicons name="power" size={14} color="#4ade80" />
                  }
                  <Text className="text-green-400 text-xs font-semibold">Encender todo</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border flex-1 justify-center ${actionLoading ? 'opacity-50' : ''} bg-red-500/15 border-red-500/30`}
                  onPress={() => handleAction('apagar')}
                  disabled={actionLoading !== null}
                  activeOpacity={0.7}
                >
                  {actionLoading === 'apagar'
                    ? <ActivityIndicator size="small" color="#f87171" />
                    : <Ionicons name="power-outline" size={14} color="#f87171" />
                  }
                  <Text className="text-red-400 text-xs font-semibold">Apagar todo</Text>
                </TouchableOpacity>

                {onScheduleRoom && (
                  <TouchableOpacity
                    className="flex-row items-center gap-1.5 px-3 py-2 rounded-lg border bg-bg border-border justify-center"
                    onPress={() => onScheduleRoom(roomId, roomName)}
                    activeOpacity={0.7}
                  >
                    <Ionicons name="time-outline" size={14} color="#94a3b8" />
                    <Text className="text-text-secondary text-xs font-semibold">Programar</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
          </View>

          {/* Device list */}
          <ScrollView className="px-4 py-4" showsVerticalScrollIndicator={false}>
            {devices.length === 0 ? (
              <View className="py-16 items-center">
                <Ionicons name="cube-outline" size={48} color="#334155" />
                <Text className="text-text-secondary text-sm mt-3 text-center">
                  No hay dispositivos en esta habitación
                </Text>
              </View>
            ) : (
              <View className="gap-3 pb-6">
                {devices.map((device) => (
                  <LinkedDeviceItem
                    key={device.id}
                    device={device}
                    onUnlink={onUnlinkDevice ?? (() => {})}
                    onDeviceUpdate={onDeviceUpdate}
                    onEditSuccess={onEditSuccess}
                  />
                ))}
              </View>
            )}
          </ScrollView>

        </View>
      </View>

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'success'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </Modal>
  );
}
