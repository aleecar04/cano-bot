import { BotScanResponse } from './bot-scan-response';
import { BotDeviceList } from './bot-device-list';
import { BotActionsList } from './bot-actions-list';
import { BotHelp } from './bot-help';

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

  if (tipo === 'help') {
    return <BotHelp secciones={(data.secciones as any[]) ?? []} />;
  }

  if (tipo === 'actions_list') {
    return (
      <BotActionsList
        device={data.device as string | undefined}
        device_type={data.device_type as string | undefined}
        label={data.label as string | undefined}
        acciones={(data.acciones as any[]) ?? undefined}
        grupos={(data.grupos as any[]) ?? undefined}
      />
    );
  }

  return null;
}
