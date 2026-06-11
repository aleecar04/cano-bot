import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { deviceIcon } from '@/utils/device-icons';

interface DeviceEntry {
  id: string;
  name: string;
  type: string;
  is_online: boolean;
  state?: Record<string, unknown>;
}

interface BotDeviceListProps {
  dispositivos: DeviceEntry[];
  total: number;
  timestamp: Date;
}

export function BotDeviceList({ dispositivos, total, timestamp }: BotDeviceListProps) {
  const formatTime = (date: Date) =>
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <View style={{ paddingHorizontal: 16, marginVertical: 4, alignItems: 'flex-start' }}>
      <View className="flex-row items-end gap-2" style={{ maxWidth: '90%' }}>
        <View className="w-8 h-8 rounded-full bg-primary/10 items-center justify-center border border-primary/20 shrink-0">
          <Ionicons name="chatbubble-ellipses" size={16} color="#3B82F6" />
        </View>

        <View className="bg-white rounded-2xl rounded-tl-none border border-border px-4 py-3">
          <View className="flex-row items-center gap-2 mb-3">
            <Ionicons name="hardware-chip" size={16} color="#3B82F6" />
            <Text className="text-slate-800 font-semibold text-sm">
              {total} dispositivo{total !== 1 ? 's' : ''} vinculado{total !== 1 ? 's' : ''}
            </Text>
          </View>

          {dispositivos.length === 0 ? (
            <Text className="text-text-secondary text-xs">No tienes dispositivos vinculados.</Text>
          ) : (
            <View className="gap-1.5">
              {dispositivos.map((d) => (
                <View
                  key={d.id}
                  className="flex-row items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2"
                >
                  <Ionicons
                    name={deviceIcon(d.type) as any}
                    size={16}
                    color={d.is_online ? '#22c55e' : '#94a3b8'}
                  />
                  <Text className="text-slate-700 text-xs font-semibold flex-1" numberOfLines={1}>
                    {d.name}
                  </Text>
                  <View className={`w-2 h-2 rounded-full ${d.is_online ? 'bg-green-400' : 'bg-slate-300'}`} />
                </View>
              ))}
            </View>
          )}

          <Text className="text-text-secondary text-[10px] font-medium mt-2">
            {formatTime(timestamp)}
          </Text>
        </View>
      </View>
    </View>
  );
}
