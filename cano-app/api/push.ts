import { getAuthHeaders } from './auth';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface PushSubscriptionPayload {
  endpoint: string;
  p256dh: string;
  auth: string;
}

export async function getVapidPublicKey(): Promise<string> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/push/vapid-public-key`, { headers });
  if (!res.ok) throw new Error('Error obteniendo clave VAPID');
  const data = await res.json();
  return data.public_key;
}

export async function savePushSubscription(sub: PushSubscriptionPayload): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/push/subscribe`, {
    method: 'POST',
    headers,
    body: JSON.stringify(sub),
  });
  if (!res.ok) throw new Error('Error guardando suscripción push');
}

export async function removePushSubscription(sub: PushSubscriptionPayload): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/push/subscribe`, {
    method: 'DELETE',
    headers,
    body: JSON.stringify(sub),
  });
  if (!res.ok) throw new Error('Error eliminando suscripción push');
}

/** Convert a base64url VAPID public key to a Uint8Array for PushManager */
export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw     = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}
