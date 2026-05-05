import { useRef, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Dimensions,
  ListRenderItem,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getMyHouse, NoHouseError } from '@/api/houses';

const { width } = Dimensions.get('window');

export const ONBOARDING_DONE_KEY = '@cano4/onboarding_done';

// ── Slides ────────────────────────────────────────────────────────────────────

interface Slide {
  id: string;
  icon: keyof typeof Ionicons.glyphMap;
  iconColor: string;
  title: string;
  subtitle: string;
}

const SLIDES: Slide[] = [
  {
    id: '1',
    icon: 'home',
    iconColor: '#3B82F6',
    title: 'Bienvenido a CanoBot',
    subtitle:
      'Tu asistente domótico inteligente. Controla todos los dispositivos de tu hogar desde un solo lugar.',
  },
  {
    id: '2',
    icon: 'chatbubbles',
    iconColor: '#8B5CF6',
    title: 'Habla con tu hogar',
    subtitle:
      'Escribe mensajes naturales: "Apaga las luces del salón", "¿Qué temperatura hace en casa?" y CanoBot lo gestiona.',
  },
  {
    id: '3',
    icon: 'scan',
    iconColor: '#10B981',
    title: 'Descubre dispositivos',
    subtitle:
      'CanoBot escanea tu red local y detecta automáticamente luces, televisores, termostatos y más.',
  },
  {
    id: '4',
    icon: 'time',
    iconColor: '#F59E0B',
    title: 'Automatiza con tareas',
    subtitle:
      'Programa acciones: apagar las luces a las 23h todos los días, encender la calefacción los lunes a las 7h…',
  },
  {
    id: '5',
    icon: 'flash',
    iconColor: '#EF4444',
    title: 'Acceso rápido',
    subtitle:
      'Añade tus acciones más usadas a la pantalla de inicio para ejecutarlas con un toque, sin buscar.',
  },
];

// ── Componentes ───────────────────────────────────────────────────────────────

function SlideItem({ item }: { item: Slide }) {
  return (
    <View style={{ width }} className="flex-1 items-center justify-center px-10 gap-6">
      <View
        className="w-28 h-28 rounded-full items-center justify-center"
        style={{ backgroundColor: item.iconColor + '20' }}
      >
        <Ionicons name={item.icon} size={56} color={item.iconColor} />
      </View>

      <View className="gap-3">
        <Text className="text-text text-2xl font-bold text-center">{item.title}</Text>
        <Text className="text-text-secondary text-base text-center leading-6">
          {item.subtitle}
        </Text>
      </View>
    </View>
  );
}

function Dots({ count, current }: { count: number; current: number }) {
  return (
    <View className="flex-row gap-2 justify-center">
      {Array.from({ length: count }).map((_, i) => (
        <View
          key={i}
          className={`h-2 rounded-full ${i === current ? 'bg-primary w-5' : 'bg-border w-2'}`}
          style={{ transition: 'all 0.2s' } as any}
        />
      ))}
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function OnboardingScreen() {
  const router = useRouter();
  const [current, setCurrent] = useState(0);
  const listRef = useRef<FlatList<Slide>>(null);
  const isLast = current === SLIDES.length - 1;

  const finish = async () => {
    await AsyncStorage.setItem(ONBOARDING_DONE_KEY, 'true');
    try {
      await getMyHouse();
      router.replace('/(tabs)' as any);
    } catch (err) {
      if (err instanceof NoHouseError) {
        router.replace('/house-setup' as any);
      } else {
        router.replace('/(tabs)' as any);
      }
    }
  };

  const next = () => {
    if (isLast) {
      finish();
      return;
    }
    const nextIndex = current + 1;
    listRef.current?.scrollToIndex({ index: nextIndex, animated: true });
    setCurrent(nextIndex);
  };

  const onScroll = (e: { nativeEvent: { contentOffset: { x: number } } }) => {
    const index = Math.round(e.nativeEvent.contentOffset.x / width);
    setCurrent(index);
  };

  const renderItem: ListRenderItem<Slide> = ({ item }) => <SlideItem item={item} />;

  return (
    <SafeAreaView className="flex-1 bg-bg">
      {/* Skip */}
      <View className="flex-row justify-end px-6 pt-2">
        {!isLast && (
          <TouchableOpacity onPress={finish} hitSlop={10}>
            <Text className="text-text-secondary text-sm font-medium">Omitir</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Slides */}
      <FlatList
        ref={listRef}
        data={SLIDES}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        className="flex-1"
        getItemLayout={(_, index) => ({ length: width, offset: width * index, index })}
      />

      {/* Footer */}
      <View className="px-8 pb-8 gap-6">
        <Dots count={SLIDES.length} current={current} />

        <TouchableOpacity
          className="bg-primary rounded-2xl py-4 items-center"
          onPress={next}
          activeOpacity={0.8}
        >
          <Text className="text-text font-semibold text-base">
            {isLast ? 'Comenzar' : 'Siguiente'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
