import { supabase } from './supabase';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

async function getAuthHeaders() {
  const { data: { session } } = await supabase.auth.getSession();
  console.log('Session:', session?.access_token ? 'token OK' : 'SIN TOKEN');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session?.access_token}`,
  };
}

export async function sendMessage(body: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/messages/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ body }),
  });
  if (!res.ok) throw new Error('Error enviando mensaje');
  return res.json();
}

export async function getMessages() {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/messages/`, { headers });
  if (!res.ok) {
    const err = await res.json();
    console.log('GET messages status:', res.status, JSON.stringify(err));
    throw new Error('Error cargando mensajes');
  }
  return res.json();
}

export async function getUserProfile() {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/users/me/profile`, { headers });
  if (!res.ok) throw new Error('Error cargando perfil');
  return res.json();
}