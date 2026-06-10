import { useEffect, useRef } from 'react';
import { Animated, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type ToastVariant = 'success' | 'error';

type Props = {
  message: string;
  variant?: ToastVariant;
  visible: boolean;
  onHide: () => void;
  duration?: number;
};

export function Toast({ message, variant = 'success', visible, onHide, duration = 3000 }: Readonly<Props>) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) return;
    Animated.sequence([
      Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.delay(duration - 400),
      Animated.timing(opacity, { toValue: 0, duration: 200, useNativeDriver: true }),
    ]).start(() => onHide());
  }, [visible]);

  if (!visible) return null;

  const isSuccess = variant === 'success';

  return (
    <Animated.View
      style={{ opacity, position: 'absolute', bottom: 32, left: 16, right: 16, zIndex: 9999 }}
      pointerEvents="none"
    >
      <View
        className={`flex-row items-center gap-3 px-4 py-3 rounded-2xl shadow-lg ${
          isSuccess ? 'bg-green-500' : 'bg-red-500'
        }`}
      >
        <Ionicons
          name={isSuccess ? 'checkmark-circle' : 'alert-circle'}
          size={20}
          color="white"
        />
        <Text className="text-white font-semibold text-sm flex-1">{message}</Text>
      </View>
    </Animated.View>
  );
}
