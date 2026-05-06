import { getAuthHeaders } from './auth';
import { supabase } from './supabase';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

// ── DTOs ─────────────────────────────────────────────────────────────────────

export interface RoomDto {
  id: string;
  floor_id: string;
  name: string;
  floor_name?: string; // populated by GET /houses/me/rooms
}

export interface FloorDto {
  id: string;
  house_id: string;
  name: string;
  level: number;
  rooms: RoomDto[];
}

export interface HouseDto {
  id: string;
  user_id: string;
  name: string | null;
  floors: FloorDto[];
}

export type HouseMemberRole = 'owner' | 'member';

export interface HouseMemberDto {
  user_id: string;
  username: string | null;
  role: HouseMemberRole;
  created_at: string;
}

export interface InviteCodeDto {
  code: string;
  expires_in_hours: number;
}

export interface JoinHouseDto {
  ok: boolean;
  house_id: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

async function throwBackendError(res: Response, fallback: string): Promise<never> {
  const err = await res.json().catch(() => ({ detail: fallback }));
  throw new Error(err.detail ?? fallback);
}

export class NoHouseError extends Error {
  constructor() { super('NO_HOUSE'); }
}

export async function getMyHouse(): Promise<HouseDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me`, { headers });
  if (res.status === 404) throw new NoHouseError();
  if (!res.ok) return throwBackendError(res, 'Error cargando casa');
  return res.json();
}

export async function getHouseMembers(): Promise<HouseMemberDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me/members`, { headers });
  if (!res.ok) return throwBackendError(res, 'Error cargando miembros');
  return res.json();
}

export async function generateInviteCode(): Promise<InviteCodeDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me/invite`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) return throwBackendError(res, 'Error generando código de invitación');
  return res.json();
}

export async function setupHouse(botJid: string): Promise<{ ok: boolean; house_id: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/setup`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ bot_jid: botJid }),
  });
  if (!res.ok) return throwBackendError(res, 'JID de bot no válido');
  return res.json();
}

export interface GeneratedBotCredentials {
  jid: string;
  password: string;
  house_id: string;
}

export async function generateBotSetup(): Promise<GeneratedBotCredentials> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/setup/generate`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) return throwBackendError(res, 'Error generando credenciales del bot');
  return res.json();
}

export async function joinHouse(code: string): Promise<JoinHouseDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/join`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ code }),
  });
  if (!res.ok) return throwBackendError(res, 'Error al unirse al hogar');
  return res.json();
}

export async function getMyRole(): Promise<HouseMemberRole | null> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const currentUserId = session?.user.id;
    if (!currentUserId) return null;
    const members = await getHouseMembers();
    const me = members.find((m) => m.user_id === currentUserId);
    return me?.role ?? null;
  } catch {
    return null;
  }
}

export async function getMyRooms(): Promise<RoomDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me/rooms`, { headers });
  if (!res.ok) return throwBackendError(res, 'Error cargando habitaciones');
  return res.json();
}

export async function addFloor(name: string, level = 0): Promise<FloorDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me/floors`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ name, level }),
  });
  if (!res.ok) return throwBackendError(res, 'Error creando planta');
  return res.json();
}

export async function addRoom(floorId: string, name: string): Promise<RoomDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/floors/${floorId}/rooms`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ name }),
  });
  if (!res.ok) return throwBackendError(res, 'Error creando habitación');
  return res.json();
}

export async function deleteRoom(floorId: string, roomId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/floors/${floorId}/rooms/${roomId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) return throwBackendError(res, 'Error eliminando habitación');
}

export async function deleteFloor(floorId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/floors/${floorId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) return throwBackendError(res, 'Error eliminando planta');
}

export async function roomAction(
  roomId: string,
  action: 'encender' | 'apagar',
): Promise<{ ok: boolean; results: any[] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/rooms/${roomId}/action`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error('Error ejecutando acción grupal');
  return res.json();
}

export async function floorAction(
  floorId: string,
  action: 'encender' | 'apagar',
): Promise<{ ok: boolean; results: any[] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/floors/${floorId}/action`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error('Error ejecutando acción grupal');
  return res.json();
}

export interface SchedulePayload {
  name: string;
  action: string;
  payload?: Record<string, unknown>;
  run_at?: string;
  cron_expr?: string;
  timezone?: string;
}

export async function roomSchedule(
  roomId: string,
  scheduleData: SchedulePayload,
): Promise<{ ok: boolean; created: number }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/rooms/${roomId}/schedule`, {
    method: 'POST',
    headers,
    body: JSON.stringify(scheduleData),
  });
  if (!res.ok) throw new Error('Error creando tarea grupal');
  return res.json();
}

export async function floorSchedule(
  floorId: string,
  scheduleData: SchedulePayload,
): Promise<{ ok: boolean; created: number }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/floors/${floorId}/schedule`, {
    method: 'POST',
    headers,
    body: JSON.stringify(scheduleData),
  });
  if (!res.ok) throw new Error('Error creando tarea grupal');
  return res.json();
}

export async function kickMember(userId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me/members/${userId}`, { method: 'DELETE', headers });
  if (!res.ok) return throwBackendError(res, 'Error al expulsar miembro');
}

export async function leaveHouse(): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/houses/me/leave`, { method: 'DELETE', headers });
  if (!res.ok) return throwBackendError(res, 'Error al salir de la casa');
}
