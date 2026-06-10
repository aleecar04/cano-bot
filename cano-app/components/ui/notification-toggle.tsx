import { useState, useEffect, type ReactNode } from 'react';
import { View, Text, Switch, ActivityIndicator, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import {
  getVapidPublicKey, savePushSubscription, removePushSubscription,
  urlBase64ToUint8Array,
} from '@/api/push';

type NotifState = 'unsupported' | 'denied' | 'enabled' | 'disabled';

async function getSubscription(): Promise<PushSubscription | null> {
  if (typeof globalThis === 'undefined' || !('serviceWorker' in navigator)) return null;
  const reg = await navigator.serviceWorker.ready.catch(() => null);
  if (!reg) return null;
  return reg.pushManager.getSubscription();
}

function toBase64Url(value: string): string {
  return value.replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}

function extractKeys(sub: PushSubscription): { p256dh: string; auth: string } {
  const p256dh = btoa(String.fromCodePoint(...new Uint8Array(sub.getKey('p256dh')!)));
  const auth   = btoa(String.fromCodePoint(...new Uint8Array(sub.getKey('auth')!)));
  return {
    p256dh: toBase64Url(p256dh),
    auth:   toBase64Url(auth),
  };
}

export function NotificationToggle() {
  const [state, setState]     = useState<NotifState>('disabled');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (Platform.OS !== 'web' || typeof globalThis === 'undefined' || !('Notification' in globalThis)) {
      setState('unsupported');
      setLoading(false);
      return;
    }
    if (Notification.permission === 'denied') {
      setState('denied');
      setLoading(false);
      return;
    }
    getSubscription().then((sub) => {
      setState(sub ? 'enabled' : 'disabled');
    }).catch(() => {
      setState('unsupported');
    }).finally(() => setLoading(false));
  }, []);

  const handleToggle = async (value: boolean) => {
    setLoading(true);
    try {
      if (value) {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          setState('denied');
          return;
        }
        const reg       = await navigator.serviceWorker.ready;
        const vapidKey  = await getVapidPublicKey();
        const sub       = await reg.pushManager.subscribe({
          userVisibleOnly:      true,
          applicationServerKey: urlBase64ToUint8Array(vapidKey),
        });
        const { p256dh, auth } = extractKeys(sub);
        await savePushSubscription({ endpoint: sub.endpoint, p256dh, auth });
        setState('enabled');
      } else {
        const sub = await getSubscription();
        if (sub) {
          const { p256dh, auth } = extractKeys(sub);
          await removePushSubscription({ endpoint: sub.endpoint, p256dh, auth });
          await sub.unsubscribe();
        }
        setState('disabled');
      }
    } catch (err) {
      console.warn('Push toggle error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (state === 'unsupported') return null;

  const statusLabels: Record<NotifState, string> = {
    enabled:     'Activadas',
    denied:      'Bloqueadas en el navegador',
    disabled:    'Desactivadas',
    unsupported: '',
  };

  let rightControl: ReactNode;
  if (loading) {
    rightControl = <ActivityIndicator size="small" color="#6366f1" />;
  } else if (state === 'denied') {
    rightControl = <Ionicons name="lock-closed-outline" size={16} color="#ef4444" />;
  } else {
    rightControl = (
      <Switch
        value={state === 'enabled'}
        onValueChange={handleToggle}
        trackColor={{ false: '#334155', true: '#6366f1' }}
        thumbColor="white"
        style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
      />
    );
  }

  return (
    <View className="flex-row items-center justify-between py-3">
      <View className="flex-row items-center gap-3 flex-1">
        <View className="w-8 h-8 rounded-lg bg-indigo-500/15 items-center justify-center">
          <Ionicons
            name={state === 'enabled' ? 'notifications' : 'notifications-outline'}
            size={16}
            color={state === 'enabled' ? '#6366f1' : '#94a3b8'}
          />
        </View>
        <View className="flex-1">
          <Text className="text-text font-semibold text-sm">Notificaciones</Text>
          <Text className="text-text-secondary text-xs mt-0.5">
            {statusLabels[state]}
          </Text>
        </View>
      </View>

      {rightControl}
    </View>
  );
}
