import { useEffect, useRef } from 'react';
import { Animated, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

function ThinkingDot({ delay }: Readonly<{ delay: number }>) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.delay(delay),
        Animated.timing(anim, { toValue: -5, duration: 300, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0, duration: 300, useNativeDriver: true }),
        Animated.delay(600 - delay),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [anim, delay]);

  return <Animated.View style={[
    { width: 7, height: 7, borderRadius: 4, backgroundColor: '#3B82F6' },
    { transform: [{ translateY: anim }] }
  ]} />;
}

export function ThinkingDots() {
  return (
    <View className="flex-row items-end gap-2 my-2 px-4">
      <View className="w-8 h-8 rounded-full bg-primary/20 items-center justify-center shrink-0">
        <Ionicons name="chatbubble" size={14} color="#3B82F6" />
      </View>
      <View className="bg-bg-secondary rounded-2xl rounded-bl-sm border border-border px-4 py-3">
        <View className="flex-row gap-1 items-center">
          <ThinkingDot delay={0} />
          <ThinkingDot delay={200} />
          <ThinkingDot delay={400} />
        </View>
      </View>
    </View>
  );
}