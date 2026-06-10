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

  return null;
}
