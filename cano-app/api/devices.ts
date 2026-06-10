import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface DeviceDto {
  id: string;
  owner_id: string;
  name: string;
  type: string;
  driver: string | null;
  ip: string | null;
  mac: string | null;
  config: Record<string, unknown>;
  estado: Record<string, unknown>;
  is_online: boolean;
  room_id: string | null;
  registered_at: string | null;
  updated_at: string | null;
}

export interface VincularDeviceParams {
  ip: string;
  mac: string;
  hostname: string;
  tipo: string;
  name: string;
  room_id?: string;
  driver?: string;
  config?: Record<string, unknown>;
}

// ── API calls ─────────────────────────────────────────────────────────────────

async function throwBackendError(res: Response, fallback: string): Promise<never> {
  const err = await res.json().catch(() => ({ detail: fallback }));
  throw new Error(err.detail ?? fallback);
}

export async function getDevices(): Promise<DeviceDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/`, { headers });
  if (!res.ok) return throwBackendError(res, 'Error cargando dispositivos');
  return res.json();
}

export async function vincularDevice(device: VincularDeviceParams): Promise<DeviceDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/vincular`, {
    method: 'POST',
    headers,
    body: JSON.stringify(device),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(error.detail ?? 'Error vinculando dispositivo');
  }
  return res.json();
}

export async function updateDevice(
  deviceId: string,
  data: { name?: string; room_id?: string | null; type?: string },
): Promise<DeviceDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/${deviceId}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) return throwBackendError(res, 'Error actualizando dispositivo');
  return res.json();
}

export async function desvincularDevice(deviceId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/${deviceId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) return throwBackendError(res, 'Error desvinculando dispositivo');
}

export async function getDevice(deviceId: string): Promise<DeviceDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/${deviceId}`, { headers });
  if (!res.ok) return throwBackendError(res, 'Dispositivo no encontrado');
  return res.json();
}

export async function refreshDevice(deviceId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/${deviceId}/refresh`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) return throwBackendError(res, 'No se pudo refrescar el dispositivo');
}

export async function sendCommand(
  deviceId: string,
  action: string,
  payload: Record<string, unknown> = {},
): Promise<{ ok: boolean; command_id: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/commands`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ action, device_id: deviceId, payload }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(error.detail ?? 'Error ejecutando comando');
  }
  return res.json();
}

export async function scanNetwork(): Promise<{ ok: boolean; command_id: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/commands`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ action: 'scan' }),
  });
  if (!res.ok) return throwBackendError(res, 'Error iniciando escaneo');
  return res.json();
}

export interface CommandDto {
  id: string;
  user_id?: string;
  device_id: string | null;
  target_type: 'device' | 'system';
  action: string;
  payload: Record<string, unknown>;
  status: 'pending' | 'sent' | 'executed' | 'failed';
  source_type: 'direct' | 'conversation' | 'favorite' | 'schedule';
  source_id: string | null;
  executed_at: string | null;
  error: string | null;
  result_data: Record<string, unknown> | null;
  created_at: string;
  devices?: { name: string; type: string } | null;
}

export interface CommandHistoryFilters {
  source_type?: CommandDto['source_type'];
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
  /** Owner-only: uuid of a specific member, or 'all' for entire house */
  member_id?: string;
}

export async function getMyCommandHistory(filters: CommandHistoryFilters = {}): Promise<CommandDto[]> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams();
  if (filters.source_type) params.set('source_type', filters.source_type);
  if (filters.date_from)   params.set('date_from', filters.date_from);
  if (filters.date_to)     params.set('date_to', filters.date_to);
  if (filters.page)        params.set('page', String(filters.page));
  if (filters.limit)       params.set('limit', String(filters.limit));
  if (filters.member_id)   params.set('member_id', filters.member_id);
  const qs = params.toString();
  const suffix = qs ? `?${qs}` : '';
  const res = await fetch(`${API_URL}/api/v1/devices/commands${suffix}`, { headers });
  if (!res.ok) return throwBackendError(res, 'Error cargando historial');
  return res.json();
}

export async function getCommand(commandId: string): Promise<CommandDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/commands/${commandId}`, { headers });
  if (!res.ok) return throwBackendError(res, 'Comando no encontrado');
  return res.json();
}

/** Polls until the bot has updated the device after vinculation (estado populated OR updated_at changed). */
export async function waitForDeviceStatus(deviceId: string, maxAttempts = 15): Promise<DeviceDto> {
  // Capture baseline updated_at so we detect when the bot first touches the device
  let baseline: string | null = null;
  try {
    baseline = (await getDevice(deviceId)).updated_at;
  } catch {}

  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const device = await getDevice(deviceId);
    if (device.estado && Object.keys(device.estado).length > 0) return device;
    // Bot touched the device (updated_at changed) even if estado is still empty (e.g. TV off)
    if (baseline && device.updated_at && device.updated_at !== baseline) return device;
  }
  return getDevice(deviceId);
}

/** Polls until command leaves "pending" state or times out (~30s). */
export async function waitForCommand(commandId: string, maxAttempts = 20): Promise<CommandDto> {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const cmd = await getCommand(commandId);
    if (cmd.status !== 'pending') return cmd;
  }
  throw new Error('timeout');
}
