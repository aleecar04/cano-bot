import { Modal, View, Text, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type DeviceDto } from '@/api/devices';
import { deviceIcon } from '@/utils/device-icons';

type ActionItem = { accion: string; icon: string; label: string };

interface AddFavoriteModalProps {
  visible: boolean;
  devices: DeviceDto[];
  step: 'device' | 'action';
  pendingDevice: DeviceDto | null;
  actionItems: ActionItem[];
  saving: boolean;
  onClose: () => void;
  onSelectDevice: (device: DeviceDto) => void;
  onSelectAction: (accion: string, label: string) => void;
  onBack: () => void;
}

export function AddFavoriteModal({
  visible, devices, step, pendingDevice, actionItems,
  saving, onClose, onSelectDevice, onSelectAction, onBack,
}: AddFavoriteModalProps) {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary rounded-t-3xl border-t border-border pb-8">
          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <View>
              <Text className="text-text text-base font-bold">
                {step === 'device' ? 'Selecciona dispositivo' : 'Selecciona acción'}
              </Text>
              {step === 'action' && pendingDevice && (
                <Text className="text-text-secondary text-xs mt-0.5">{pendingDevice.name}</Text>
              )}
            </View>
            <View className="flex-row items-center gap-3">
              {step === 'action' && (
                <TouchableOpacity onPress={onBack} disabled={saving}>
                  <Ionicons name="arrow-back" size={20} color="#94a3b8" />
                </TouchableOpacity>
              )}
              <TouchableOpacity onPress={onClose} disabled={saving}>
                <Ionicons name="close" size={22} color="#94a3b8" />
              </TouchableOpacity>
            </View>
          </View>

          <ScrollView className="px-5 pt-4" style={{ maxHeight: 320 }} showsVerticalScrollIndicator={false}>
            {step === 'device' ? (
              devices.length === 0 ? (
                <View className="py-8 items-center">
                  <Text className="text-text-secondary text-sm">No tienes dispositivos vinculados</Text>
                </View>
              ) : (
                devices.map((d) => (
                  <TouchableOpacity
                    key={d.id}
                    onPress={() => onSelectDevice(d)}
                    className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-2"
                    activeOpacity={0.7}
                  >
                    <Ionicons name={deviceIcon(d.type) as any} size={20} color="#94a3b8" />
                    <View className="flex-1">
                      <Text className="text-text font-semibold text-sm">{d.name}</Text>
                      <Text className="text-text-secondary text-xs">{d.type}</Text>
                    </View>
                    <View className={`px-2 py-0.5 rounded-full ${d.is_online ? 'bg-green-500/15' : 'bg-bg'}`}>
                      <Text className={`text-xs font-semibold ${d.is_online ? 'text-green-400' : 'text-text-secondary'}`}>
                        {d.is_online ? 'Online' : 'Offline'}
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))
              )
            ) : (
              actionItems.map(({ accion, icon, label }) => (
                <TouchableOpacity
                  key={accion}
                  onPress={() => onSelectAction(accion, label)}
                  disabled={saving}
                  className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-2"
                  activeOpacity={0.7}
                >
                  {saving
                    ? <ActivityIndicator size="small" color="#6366f1" />
                    : <Ionicons name={icon as any} size={20} color="#6366f1" />
                  }
                  <Text className="text-text font-semibold text-sm">{label}</Text>
                </TouchableOpacity>
              ))
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
