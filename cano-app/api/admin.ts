import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

// ── DTOs ─────────────────────────────────────────────────────────────────────

export interface AdminHouseDto {
  id: string;
  name: string | null;
  bot_jid: string | null;
  member_count: number;
  owner: { username: string; email: string } | null;
  created_at: string;
}

export interface AdminOwnerDto {
  id: string;
  username: string;
  email: string;
}

export interface AdminDeviceDto {
  id: string;
  owner_id: string;
  name: string;
  type: string;
  driver: string | null;
  ip: string;
  is_online: boolean;
  room_id: string | null;
  room_name: string | null;
  floor_name: string | null;
  registered_at: string | null;
  owner: AdminOwnerDto | null;
}

export interface AdminCommandDto {
  id: string;
  user_id: string;
  device_id: string | null;
  action: string;
  payload: Record<string, unknown> | null;
  status: 'pending' | 'sent' | 'executed' | 'failed';
  source_type: 'direct' | 'conversation' | 'favorite' | 'schedule';
  source_id: string | null;
  executed_at: string | null;
  error: string | null;
  created_at: string;
  user: AdminOwnerDto | null;
  device: { id: string; name: string; type: string } | null;
}

export interface AdminScheduleDto {
  id: string;
  user_id: string;
  device_id: string;
  name: string;
  action: string;
  payload: Record<string, unknown>;
  cron_expr: string | null;
  next_run_at: string;
  is_active: boolean;
  last_command_id: string | null;
  created_at: string;
  user: AdminOwnerDto | null;
  device: { id: string; name: string; type: string } | null;
}

export interface AdminStatsDto {
  users: number;
  devices: number;
  devices_online: number;
  devices_offline: number;
  schedules: number;
  schedules_active: number;
  commands: number;
}

// ── Filters ───────────────────────────────────────────────────────────────────

export interface DeviceFilters {
  user_id?: string;
  is_online?: boolean;
  device_type?: string;
}

export interface CommandFilters {
  user_id?: string;
  date_from?: string;
  date_to?: string;
  status?: string;
  limit?: number;
}

export interface ScheduleFilters {
  user_id?: string;
  is_active?: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildParams(filters: object): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(filters) as [string, unknown][]) {
    if (v !== undefined && v !== null && v !== '') {
      p.set(k, String(v));
    }
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getAdminStats(): Promise<AdminStatsDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/admin/stats`, { headers });
  if (!res.ok) throw new Error('Error cargando estadísticas');
  return res.json();
}

export async function getAdminDevices(filters: DeviceFilters = {}): Promise<AdminDeviceDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/admin/devices${buildParams(filters)}`, { headers });
  if (!res.ok) throw new Error('Error cargando dispositivos');
  const body = await res.json();
  return body.data;
}

export async function getAdminCommands(filters: CommandFilters = {}): Promise<AdminCommandDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/admin/commands${buildParams(filters)}`, { headers });
  if (!res.ok) throw new Error('Error cargando acciones');
  const body = await res.json();
  return body.data;
}

export async function getAdminSchedules(filters: ScheduleFilters = {}): Promise<AdminScheduleDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/admin/schedules${buildParams(filters)}`, { headers });
  if (!res.ok) throw new Error('Error cargando tareas');
  const body = await res.json();
  return body.data;
}


export async function getAdminHouses(): Promise<AdminHouseDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/admin/houses`, { headers });
  if (!res.ok) throw new Error('Error cargando casas');
  const body = await res.json();
  return body.data;
}

export async function deleteAdminHouse(houseId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/admin/houses/${houseId}`, { method: 'DELETE', headers });
  if (!res.ok) throw new Error('Error eliminando casa');
}
