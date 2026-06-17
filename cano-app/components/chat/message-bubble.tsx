import { useEffect, useRef } from 'react';
import { Animated, Text, View, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export type Message = {
  id: string;
  from: string;
  text?: string;
  result?: Record<string, unknown>;
  timestamp: Date;
};

type Section = { title: string; items: string[] };

// Convierte el texto del bot ("Sección:\n  • item") en intro + secciones,
// para poder pintarlo en cajitas. Una línea con ":" solo es título de sección
// si la siguiente línea con contenido es una viñeta.
function parseSections(text: string): { intro: string; sections: Section[] } {
  const lines = text.split('\n');
  const intro: string[] = [];
  const sections: Section[] = [];
  let current: Section | null = null;

  const nextIsBullet = (from: number) => {
    for (let j = from + 1; j < lines.length; j++) {
      const l = lines[j].trim();
      if (l) return l.startsWith('•');
    }
    return false;
  };

  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (!line) return;
    if (line.startsWith('•')) {
      const item = line.replace(/^•\s*/, '');
      if (current) current.items.push(item);
      else intro.push(item);
    } else if (line.endsWith(':') && nextIsBullet(i)) {
      current = { title: line.slice(0, -1), items: [] };
      sections.push(current);
    } else {
      current = null;
      intro.push(line);
    }
  });

  return { intro: intro.join('\n').trim(), sections };
}

export function MessageBubble({ item }: Readonly<{ item: Message }>) {
  const isMe = item.from === 'me';
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(isMe ? 25 : -25)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 250,
        useNativeDriver: Platform.OS !== 'web',
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        tension: 50,
        friction: 7,
        useNativeDriver: Platform.OS !== 'web',
      }),
    ]).start();
  }, []);

  const formatTime = (date: Date) =>
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const structured = !isMe && !!item.text && item.text.includes('•');
  const { intro, sections } = structured
    ? parseSections(item.text as string)
    : { intro: '', sections: [] as Section[] };

  return (
    <Animated.View
      style={{
        opacity: fadeAnim,
        transform: [{ translateX: slideAnim }],
        width: '100%',
        alignItems: isMe ? 'flex-end' : 'flex-start',
        paddingHorizontal: 16,
        marginVertical: 4,
      }}
    >
      <View className="flex-row items-end gap-2" style={{ maxWidth: '85%' }}>
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
          {structured ? (
            <View style={{ gap: 6 }}>
              {!!intro && (
                <Text className="text-[15px] leading-5 text-slate-800">{intro}</Text>
              )}
              {sections.map((s) => (
                <View key={s.title} className="bg-slate-100 border border-slate-200 rounded-xl px-3 py-2">
                  <Text className="text-[13px] font-bold text-slate-800 mb-0.5">{s.title}</Text>
                  {s.items.map((it) => (
                    <Text key={it} className="text-[13px] leading-5 text-slate-600">
                      {'•'} {it}
                    </Text>
                  ))}
                </View>
              ))}
            </View>
          ) : (
            <Text className={`text-[15px] leading-5 ${isMe ? 'text-white' : 'text-slate-800'}`}>
              {item.text}
            </Text>
          )}

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
