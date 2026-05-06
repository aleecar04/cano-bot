import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface FavoriteDto {
  id: string;
  user_id: string;
  device_id: string;
  action: string;
  payload: Record<string, unknown>;
  label: string | null;
  position: number;
  created_at: string | null;
  devices: { name: string; type: string } | null;
}

export interface AddFavoriteParams {
  device_id: string;
  action: string;
  payload?: Record<string, unknown>;
  label?: string;
}

export async function getFavorites(): Promise<FavoriteDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/favorite-actions/`, { headers });
  if (!res.ok) throw new Error('Error cargando favoritos');
  return res.json();
}

export async function addFavorite(params: AddFavoriteParams): Promise<FavoriteDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/favorite-actions/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(err.detail ?? 'Error guardando favorito');
  }
  return res.json();
}

export async function executeFavorite(id: string): Promise<{ ok: boolean; command_id: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/favorite-actions/${id}/execute`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error('Error ejecutando favorito');
  return res.json();
}

export async function updateFavorite(id: string, params: { action: string; payload?: Record<string, unknown>; label?: string }): Promise<FavoriteDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/favorite-actions/${id}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error('Error actualizando favorito');
  return res.json();
}

export async function deleteFavorite(id: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/favorite-actions/${id}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error('Error eliminando favorito');
}
