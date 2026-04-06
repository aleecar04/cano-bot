import { Tabs } from 'expo-router';
import React from 'react';

import { HapticTab } from '@/components/haptic-tab';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import "../../global.css"

export default function TabLayout() {
  const colorScheme = useColorScheme();

  const colors = Colors[colorScheme ?? 'light'];

  return (
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
          title: 'Home',
          tabBarIcon: ({ color, focused }) => <IconSymbol size={28} name={focused ? "house.fill" : "house"} color={color} />,
        }}
      />
      <Tabs.Screen
        name="my-panel"
        options={{
          title: 'Mi Panel',
          tabBarIcon: ({ color, focused }) => <IconSymbol size={28} name={focused ? "checkmark.circle.fill" : "checkmark.circle"} color={color} />,
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat',
          tabBarIcon: ({ color, focused }) => <IconSymbol size={28} name={focused ? "bubble.left.fill" : "bubble.left"} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color, focused }) => <IconSymbol size={28} name={focused ? "person.circle.fill" : "person.circle"} color={color} />,
        }}
      />
    </Tabs>
  );
}
