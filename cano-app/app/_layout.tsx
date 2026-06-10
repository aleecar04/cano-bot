import "../global.css"
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { supabase } from '../api/supabase';
import { Session } from '@supabase/supabase-js';
import { UserProfileProvider, useUserProfile } from '@/context/user-profile';
import { getMyHouse, NoHouseError } from '@/api/houses';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  return (
    <UserProfileProvider>
      <RootLayoutInner />
    </UserProfileProvider>
  );
}

function RootLayoutInner() {
  const colorScheme = useColorScheme();
  const router = useRouter();
  const segments = useSegments();
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const { loadProfile, clearProfile } = useUserProfile();

  useEffect(() => {
    setMounted(true);
    // Register Service Worker for Web Push
    if (Platform.OS === 'web' && typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch((err) => {
        console.warn('SW registration failed:', err);
      });
    }
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) loadProfile();
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session) {
        loadProfile();
      } else {
        clearProfile();
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!mounted || loading) return;

    const seg0 = (segments[0] as string) ?? '';
    const inAuth  = seg0 === 'login' || seg0 === 'register' || seg0 === 'forgot-password';
    const inReset = seg0 === 'reset-password';
    const inSetup = seg0 === 'house-setup';

    if (!session) {
      if (!inAuth && !inReset) router.replace('/login' as any);
      return;
    }

    if (inSetup || inReset) return;

    (async () => {
      try {
        await getMyHouse();
        if (inAuth) router.replace('/(tabs)' as any);
      } catch (err) {
        if (err instanceof NoHouseError) {
          router.replace('/house-setup' as any);
        } else if (inAuth) {
          router.replace('/(tabs)' as any);
        }
      }
    })();
  }, [mounted, session, loading]);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="register" options={{ headerShown: false }} />
        <Stack.Screen name="forgot-password" options={{ headerShown: false }} />
        <Stack.Screen name="reset-password" options={{ headerShown: false }} />
        <Stack.Screen name="house-setup" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}