import { useEffect, useRef } from 'react';
import { Animated, Text, View, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export type Message = {
  id: string;
  from: string;
  text: string;
  timestamp: Date;
};

export function MessageBubble({ item }: Readonly<{ item: Message }>) {
  const isMe = item.from === 'me';
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(isMe ? 25 : -25)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { 
        toValue: 1, 
        duration: 250, 
        useNativeDriver: Platform.OS !== 'web' 
      }),
      Animated.spring(slideAnim, { 
        toValue: 0, 
        tension: 50, 
        friction: 7, 
        useNativeDriver: Platform.OS !== 'web' 
      }),
    ]).start();
  }, []);

  const formatTime = (date: Date) =>
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <Animated.View
      style={{
        opacity: fadeAnim,
        transform: [{ translateX: slideAnim }],
        width: '100%',
        // Esta es la clave: alinear el bloque entero
        alignItems: isMe ? 'flex-end' : 'flex-start',
        paddingHorizontal: 16,
        marginVertical: 4,
      }}
    >
      <View 
        // Eliminamos el flex-row-reverse que causaba la compresión extraña
        className="flex-row items-end gap-2"
        style={{ maxWidth: '85%' }} 
      >
        {/* Avatar solo para el bot */}
        {!isMe && (
          <View className="w-8 h-8 rounded-full bg-primary/10 items-center justify-center border border-primary/20 shrink-0">
            <Ionicons name="chatbubble-ellipses" size={16} color="#3B82F6" />
          </View>
        )}

        <View
          className={`px-4 py-2.5 shadow-sm ${
            isMe
              ? 'bg-primary rounded-2xl rounded-tr-none'
              : 'bg-white rounded-2xl rounded-tl-none border border-border'
          }`}
          style={{ flexShrink: 1 }}
        >
          <Text
            className={`text-[15px] leading-5 ${isMe ? 'text-white' : 'text-slate-800'}`}
          >
            {item.text}
          </Text>
          
          <Text 
            className={`text-[10px] mt-1 font-medium ${
              isMe ? 'text-blue-100/90 text-right' : 'text-text-secondary'
            }`}
          >
            {formatTime(item.timestamp)}
          </Text>
        </View>
      </View>
    </Animated.View>
  );
}