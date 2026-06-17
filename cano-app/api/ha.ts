import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface HaConnectionDto {
  connected: boolean;
  ha_url?: string;
  created_at?: string;
}

export interface HaConnectResult {
  ok: boolean;
  // El bot (en la red local) hace la importación de forma asíncrona.
  pending?: boolean;
  importados?: number;
}

export async function getHaConnection(): Promise<HaConnectionDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/ha/connection`, { headers });
  if (!res.ok) throw new Error('Error consultando conexión HA');
  return res.json();
}

export async function connectHa(ha_url: string, token: string): Promise<HaConnectResult> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/ha/connect`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ha_url, token }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error conectando con Home Assistant' }));
    throw new Error(err.detail ?? 'Error conectando con Home Assistant');
  }
  return res.json();
}

export async function reimportHa(): Promise<HaConnectResult> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/ha/reimport`, { method: 'POST', headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error reimportando dispositivos' }));
    throw new Error(err.detail ?? 'Error reimportando dispositivos');
  }
  return res.json();
}

export async function disconnectHa(): Promise<{ ok: boolean }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/devices/ha/connection`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error('Error desconectando Home Assistant');
  return res.json();
}
