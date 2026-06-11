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
  xmpp_jid: string | null;
}

export async function getUserProfile(): Promise<UserProfileDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/users/me/profile`, { headers });
  if (!res.ok) throw new Error('Error cargando perfil');
  return res.json();
}


export interface XmppCredentialsDto {
  xmpp_jid: string;
  xmpp_password: string;
}

export async function regenerateXmppPassword(): Promise<XmppCredentialsDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/users/me/xmpp/regenerate-password`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error('No se pudo regenerar la contraseña XMPP');
  return res.json();
}
