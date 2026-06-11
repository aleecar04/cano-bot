import { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getMyRooms, type RoomDto } from '@/api/houses';
import { getDevices, vincularDevice, type DeviceDto, type VincularDeviceParams } from '@/api/devices';
import { deviceIcon } from '@/utils/device-icons';
import { friendlyError } from '@/utils/friendly-error';
import { Toast } from '@/components/ui/toast';
import { LinkDeviceModal } from '@/components/devices/link-device-modal';

interface ScannedDevice {
  ip: string;
  mac: string;
  hostname: string;
  tipo: string;
}

interface BotScanResponseProps {
  red: string;
  dispositivos: ScannedDevice[];
  total: number;
  timestamp: Date;
}

export function BotScanResponse({ red, dispositivos, total, timestamp }: Readonly<BotScanResponseProps>) {
  const [pendingDevice, setPendingDevice] = useState<ScannedDevice | null>(null);
  const [rooms, setRooms] = useState<RoomDto[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [linking, setLinking] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'error' } | null>(null);
  const [linkedDevices, setLinkedDevices] = useState<DeviceDto[]>([]);

  useEffect(() => {
    getDevices().then(setLinkedDevices).catch(() => {});
  }, []);

  const handleVincular = async (device: ScannedDevice) => {
    try {
      const roomList = await getMyRooms();
      setRooms(roomList);
    } catch {
      setRooms([]);
    }
    setPendingDevice(device);
    setShowModal(true);
  };

  const handleConfirm = async (params: VincularDeviceParams) => {
    setLinking(true);
    try {
      const result = await vincularDevice(params);
      setLinkedDevices((prev) => [...prev, result]);
      setShowModal(false);
      setPendingDevice(null);
      setToast({ message: `${params.name} vinculado correctamente`, variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setLinking(false);
    }
  };

  const formatTime = (date: Date) =>
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <View style={{ paddingHorizontal: 16, marginVertical: 4, alignItems: 'flex-start' }}>
      <View className="flex-row items-end gap-2" style={{ maxWidth: '90%' }}>
        {/* Bot avatar */}
        <View className="w-8 h-8 rounded-full bg-primary/10 items-center justify-center border border-primary/20 shrink-0">
          <Ionicons name="chatbubble-ellipses" size={16} color="#3B82F6" />
        </View>

        <View className="bg-white rounded-2xl rounded-tl-none border border-border px-4 py-3">
          {/* Header */}
          <View className="flex-row items-center gap-2 mb-3">
            <Ionicons name="wifi" size={16} color="#3B82F6" />
            <Text className="text-slate-800 font-semibold text-sm">
              {total} dispositivo{total === 1 ? '' : 's'} en {red}
            </Text>
          </View>

          {dispositivos.length === 0 ? (
            <Text className="text-text-secondary text-xs">No se encontraron dispositivos.</Text>
          ) : (
            <View className="gap-2">
              {dispositivos.map((d) => {
                const isLinked = linkedDevices.some((ld) => ld.ip === d.ip);
                return (
                  <View
                    key={d.ip}
                    className={`flex-row items-center justify-between border rounded-xl px-3 py-2 gap-3 ${
                      isLinked ? 'bg-bg-secondary border-slate-200/60' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <View className="flex-row items-center gap-2 flex-1">
                      <Ionicons
                        name={deviceIcon(d.tipo) as any}
                        size={18}
                        color={isLinked ? '#94a3b8' : '#64748b'}
                      />
                      <View className="flex-1">
                        <Text className={`text-xs font-semibold ${isLinked ? 'text-text-secondary' : 'text-slate-800'}`} numberOfLines={1}>
                          {d.hostname}
                        </Text>
                        <Text className="text-text-secondary text-xs">{d.ip}</Text>
                        {!!(d.tipo && d.tipo !== 'Dispositivo') && (
                          <Text className={`text-xs ${isLinked ? 'text-text-secondary' : 'text-indigo-500'}`}>{d.tipo}</Text>
                        )}
                      </View>
                    </View>
                    {isLinked ? (
                      <View className="rounded-lg px-2.5 py-1.5 flex-row items-center gap-1 bg-slate-200">
                        <Ionicons name="checkmark-circle" size={12} color="#94a3b8" />
                        <Text className="text-text-secondary text-xs font-semibold">Vinculado</Text>
                      </View>
                    ) : (
                      <TouchableOpacity
                        className="bg-indigo-500 rounded-lg px-2.5 py-1.5 flex-row items-center gap-1"
                        onPress={() => handleVincular(d)}
                        activeOpacity={0.7}
                      >
                        <Ionicons name="link" size={12} color="white" />
                        <Text className="text-text text-xs font-semibold">Vincular</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                );
              })}
            </View>
          )}

          <Text className="text-text-secondary text-[10px] font-medium mt-2">
            {formatTime(timestamp)}
          </Text>
        </View>
      </View>

      {pendingDevice && (
        <LinkDeviceModal
          visible={showModal}
          device={pendingDevice}
          rooms={rooms}
          linking={linking}
          onClose={() => { setShowModal(false); setPendingDevice(null); }}
          onConfirm={handleConfirm}
        />
      )}

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'success'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </View>
  );
}
