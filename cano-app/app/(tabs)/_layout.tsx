import { Tabs, useRouter } from 'expo-router';
import React, { useEffect } from 'react';
import { View, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getMyHouse, NoHouseError } from '@/api/houses';

import { HapticTab } from '@/components/haptic-tab';
import { AppHeader } from '@/components/ui/app-header';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { useKeyboardVisible } from '@/hooks/use-keyboard-visible';
import "../../global.css"

function FlashIcon({ color, focused }: Readonly<{ color: string; focused: boolean }>) {
  return <Ionicons name={focused ? 'flash-sharp' : 'flash-outline'} size={28} color={color} />;
}
function GridIcon({ color, focused }: Readonly<{ color: string; focused: boolean }>) {
  return <Ionicons name={focused ? 'grid-sharp' : 'grid-outline'} size={28} color={color} />;
}
function HomeIcon({ color, focused }: Readonly<{ color: string; focused: boolean }>) {
  return <Ionicons name={focused ? 'home-sharp' : 'home-outline'} size={28} color={color} />;
}
function ChatIcon({ color, focused }: Readonly<{ color: string; focused: boolean }>) {
  return <Ionicons name={focused ? 'chatbox-sharp' : 'chatbox-outline'} size={28} color={color} />;
}
function PersonIcon({ color, focused }: Readonly<{ color: string; focused: boolean }>) {
  return <Ionicons name={focused ? 'person-sharp' : 'person-outline'} size={28} color={color} />;
}

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();

  useEffect(() => {
    getMyHouse().catch((err) => {
      // Only redirect to house-setup for 404 (no house).
      // 401 (not authenticated) is handled by the root layout.
      if (err instanceof NoHouseError) {
        router.replace('/house-setup' as any);
      }
    });
  }, []);

  const colors = Colors[colorScheme ?? 'light'];
  const keyboardVisible = useKeyboardVisible();

  return (
    <KeyboardAvoidingView
      className="flex-1"
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={0}
    >
      <View className="flex-1">
      <AppHeader />
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: colors.tabIconSelected,
          tabBarInactiveTintColor: colors.tabIconDefault,
          headerShown: false,
          tabBarButton: HapticTab,
          tabBarStyle: {
            backgroundColor: colors.footerBackground,
            borderTopColor: '#1E293B',
            borderTopWidth: 1,
            height: 60,
            paddingBottom: 8,
            // Oculta el footer mientras el teclado está abierto (web/PWA), para que
            // el teclado lo tape sin que el footer "salte" hacia arriba.
            display: keyboardVisible ? 'none' : 'flex',
          },
        }}>
        <Tabs.Screen
          name="index"
          options={{
            title: 'Acciones rápidas',
            tabBarIcon: FlashIcon,
          }}
        />
        <Tabs.Screen
          name="my-panel"
          options={{
            title: 'Mi Panel',
            tabBarIcon: GridIcon,
          }}
        />
        <Tabs.Screen
          name="casa"
          options={{
            title: 'Casa',
            tabBarIcon: HomeIcon,
          }}
        />
        <Tabs.Screen
          name="chat"
          options={{
            title: 'Chat',
            tabBarIcon: ChatIcon,
          }}
        />
        <Tabs.Screen
          name="profile"
          options={{
            title: 'Perfil',
            href: null,
            tabBarIcon: PersonIcon,
          }}
        />
      </Tabs>
      </View>
    </KeyboardAvoidingView>
  );
}
