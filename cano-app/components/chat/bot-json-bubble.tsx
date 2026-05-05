import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { BotScanResponse } from './bot-scan-response';
import { BotDeviceList } from './bot-device-list';

interface BotJsonBubbleProps {
  data: Record<string, unknown>;
  timestamp: Date;
}

export function BotJsonBubble({ data, timestamp }: Readonly<BotJsonBubbleProps>) {
  const tipo = data.tipo as string | undefined;

  if (tipo === 'scan_response') {
    return (
      <BotScanResponse
        red={(data.red as string) ?? ''}
        ip_bot={(data.ip_bot as string | null) ?? null}
        dispositivos={(data.dispositivos as any[]) ?? []}
        total={(data.total as number) ?? 0}
        timestamp={timestamp}
      />
    );
  }

  if (tipo === 'device_list') {
    return (
      <BotDeviceList
        dispositivos={(data.dispositivos as any[]) ?? []}
        total={(data.total as number) ?? 0}
        timestamp={timestamp}
      />
    );
  }

  if (tipo === 'error') {
    const formatTime = (date: Date) =>
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    return (
      <View style={{ paddingHorizontal: 16, marginVertical: 4, alignItems: 'flex-start' }}>
        <View className="flex-row items-end gap-2" style={{ maxWidth: '85%' }}>
          <View className="w-8 h-8 rounded-full bg-primary/10 items-center justify-center border border-primary/20 shrink-0">
            <Ionicons name="chatbubble-ellipses" size={16} color="#3B82F6" />
          </View>
          <View className="bg-red-50 border border-red-200 rounded-2xl rounded-tl-none px-4 py-2.5">
            <View className="flex-row items-center gap-1.5 mb-1">
              <Ionicons name="alert-circle" size={14} color="#ef4444" />
              <Text className="text-red-600 text-xs font-semibold">Error</Text>
            </View>
            <Text className="text-red-700 text-[15px] leading-5">
              {(data.mensaje as string) ?? 'Error desconocido'}
            </Text>
            <Text className="text-red-400 text-[10px] font-medium mt-1">
              {formatTime(timestamp)}
            </Text>
          </View>
        </View>
      </View>
    );
  }

  return null;
}
