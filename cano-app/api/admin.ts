import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

// ── DTOs ─────────────────────────────────────────────────────────────────────

export interface AdminOwnerDto {
  id: string;
  username: string;
  email: string;
}

export interface AdminHouseDto {
  id: string;
  name: string | null;
  member_count: number;
  device_count: number;
  owner: { username: string; email: string } | null;
  created_at: string;
}

export interface AdminUserDto {
  id: string;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  is_superuser: boolean;
  created_at: string | null;
}

export interface AdminStatsDto {
  users: number;
  houses: number;
  devices: number;
  devices_online: number;
  devices_offline: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function request(path: string, init?: RequestInit) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...headers, ...(init?.headers ?? {}) } });
  if (!res.ok) throw new Error(`HTTP ${res.status} en ${path}`);
  return res;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getAdminStats(): Promise<AdminStatsDto> {
  const res = await request('/api/v1/admin/stats');
  return res.json();
}

export async function getAdminHouses(): Promise<AdminHouseDto[]> {
  const res = await request('/api/v1/admin/houses');
  const body = await res.json();
  return body.data;
}

export async function deleteAdminHouse(houseId: string): Promise<void> {
  await request(`/api/v1/admin/houses/${houseId}`, { method: 'DELETE' });
}

export async function getAdminUsers(): Promise<AdminUserDto[]> {
  const res = await request('/api/v1/users/?limit=500');
  const body = await res.json();
  return body.data ?? body;
}

export async function deleteAdminUser(userId: string): Promise<void> {
  await request(`/api/v1/users/${userId}`, { method: 'DELETE' });
}
