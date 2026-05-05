import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface ScheduleDto {
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
  last_command: { status: string; error: string | null; executed_at: string | null } | null;
  created_at: string | null;
  devices?: { name: string; type: string };
}

export interface CreateScheduleParams {
  device_id: string;
  name: string;
  action: string;
  payload?: Record<string, unknown>;
  run_at?: string;       // one-time: ISO datetime
  cron_expr?: string;    // recurring: cron expression
  timezone?: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getSchedules(): Promise<ScheduleDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/schedules/`, { headers });
  if (!res.ok) throw new Error('Error cargando tareas');
  return res.json();
}

export async function createSchedule(params: CreateScheduleParams): Promise<ScheduleDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/schedules/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(err.detail ?? 'Error creando tarea');
  }
  return res.json();
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/schedules/${scheduleId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error('Error eliminando tarea');
}

export async function toggleSchedule(scheduleId: string, isActive: boolean): Promise<ScheduleDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/schedules/${scheduleId}/toggle`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!res.ok) throw new Error('Error actualizando tarea');
  return res.json();
}
