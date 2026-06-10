import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { STYLES } from '@/constants/styles';

interface DeviceEmptyStateProps {
  title?: string;
  subtitle?: string;
}

export const DeviceEmptyState: React.FC<DeviceEmptyStateProps> = ({
  title = 'No hay dispositivos vinculados aún',
  subtitle = 'Escanea tu red para vincular dispositivos',
}) => {
  return (
    <View className="bg-bg-secondary border border-border rounded-xl p-6 items-center">
      <Ionicons name="link" size={56} color="#94a3b8" />
      <Text className={`${STYLES.text.secondary} text-sm text-center mt-2`}>
        {title}
      </Text>
      <Text className={`${STYLES.text.secondary} text-xs text-center mt-2`}>
        {subtitle}
      </Text>
    </View>
  );
};
