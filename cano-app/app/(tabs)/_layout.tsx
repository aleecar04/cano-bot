import { Tabs } from 'expo-router';
import React from 'react';
import { View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { HapticTab } from '@/components/haptic-tab';
import { AppHeader } from '@/components/ui/app-header';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import "../../global.css"

export default function TabLayout() {
  const colorScheme = useColorScheme();

  const colors = Colors[colorScheme ?? 'light'];

  return (
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
          },
        }}>
        <Tabs.Screen
          name="index"
          options={{
            title: 'Acciones rápidas',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'flash-sharp' : 'flash-outline'} size={28} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="my-panel"
          options={{
            title: 'Mi Panel',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'grid-sharp' : 'grid-outline'} size={28} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="casa"
          options={{
            title: 'Casa',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'home-sharp' : 'home-outline'} size={28} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="chat"
          options={{
            title: 'Chat',
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'chatbox-sharp' : 'chatbox-outline'} size={28} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="profile"
          options={{
            title: 'Perfil',
            href: null,
            tabBarIcon: ({ color, focused }) => (
              <Ionicons name={focused ? 'person-sharp' : 'person-outline'} size={28} color={color} />
            ),
          }}
        />
      </Tabs>
    </View>
  );
}
