import { getAuthHeaders } from './auth';
import type { CommandDto } from './devices';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export interface MessageDto {
  id: string;
  conversation_id: string;
  body: string;
  response: string | null;
  command_id: string | null;
  command: CommandDto | null;
  created_at: string;
}

export interface ConversationDto {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export async function createConversation(title?: string): Promise<ConversationDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/conversations/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ title: title ?? 'Nueva conversación' }),
  });
  if (!res.ok) throw new Error('Error creando conversación');
  return res.json();
}

export async function getConversations(): Promise<ConversationDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/conversations/`, { headers });
  if (!res.ok) throw new Error('Error cargando conversaciones');
  return res.json();
}

export async function getConversationMessages(conversationId: string): Promise<MessageDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/conversations/${conversationId}/messages`, { headers });
  if (!res.ok) throw new Error('Error cargando mensajes');
  return res.json();
}

// ── Messages ──────────────────────────────────────────────────────────────────

export async function sendMessage(body: string, conversationId: string): Promise<MessageDto> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/messages/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ body, conversation_id: conversationId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error enviando mensaje' }));
    throw new Error(err.detail ?? 'Error enviando mensaje');
  }
  return res.json();
}

export async function getMessages(): Promise<MessageDto[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/api/v1/messages/`, { headers });
  if (!res.ok) throw new Error('Error cargando mensajes');
  return res.json();
}
