import "../global.css"
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { supabase } from '../api/supabase';
import { Session } from '@supabase/supabase-js';
import { ONBOARDING_DONE_KEY } from './onboarding';
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
    const inAuth  = seg0 === 'login' || seg0 === 'register';
    const inSetup = seg0 === 'house-setup' || seg0 === 'onboarding';

    if (!session) {
      if (!inAuth) router.replace('/login' as any);
      return;
    }

    // Already in a setup flow — don't interfere
    if (inSetup) return;

    // Authenticated: check onboarding then house for every entry point
    AsyncStorage.getItem(ONBOARDING_DONE_KEY).then(async (done) => {
      if (!done) {
        router.replace('/onboarding' as any);
        return;
      }
      try {
        await getMyHouse();
        if (inAuth) router.replace('/(tabs)' as any);
      } catch (err) {
        // Only redirect to house-setup for 404 (no house configured)
        if (err instanceof NoHouseError) {
          router.replace('/house-setup' as any);
        } else if (inAuth) {
          // Other errors coming from auth → go to tabs anyway
          router.replace('/(tabs)' as any);
        }
      }
    });
  }, [mounted, session, loading]);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="register" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding" options={{ headerShown: false }} />
        <Stack.Screen name="house-setup" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}