import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface UserProfileDto {
  id: string;
  email: string | null;
  username: string | null;
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean | null;
  is_superuser: boolean | null;
  xmpp_jid: string | null;
}

export async function getUserProfile(): Promise<UserProfileDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/users/me/profile`, { headers });
  if (!res.ok) throw new Error('Error cargando perfil');
  return res.json();
}
