import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  TextInput,
  FlatList,
  Text,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Animated,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { sendMessage as apiSendMessage, getMessages } from '../../api/api';
import { supabase } from '../../api/supabase';
import { STYLES } from '../../constants/styles';

type Message = {
  id: string;
  from: string;
  text: string;
  timestamp: Date;
};

function ThinkingDot({ delay }: { delay: number }) {
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
  return <Animated.View style={[styles.dot, { transform: [{ translateY: anim }] }]} />;
}

function MessageBubble({ item }: { item: Message }) {
  const isMe = item.from === 'me';
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(isMe ? 20 : -20)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.spring(slideAnim, { toValue: 0, tension: 80, friction: 10, useNativeDriver: true }),
    ]).start();
  }, [fadeAnim, slideAnim]);

  const formatTime = (date: Date) =>
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <Animated.View
      className={`flex-row my-1 items-end gap-2 ${isMe ? 'justify-end' : 'justify-start'}`}
      style={{ opacity: fadeAnim, transform: [{ translateX: slideAnim }] }}
    >
      {!isMe && (
        <View className="w-8 h-8 rounded-full bg-bg-secondary items-center justify-center border border-border">
          <Text className="text-sm">🤖</Text>
        </View>
      )}
      <View
        className={`rounded-2xl px-4 py-3 ${
          isMe
            ? 'bg-primary rounded-br-sm'
            : 'bg-bg-secondary rounded-bl-sm border border-border'
        }`}
        style={{ maxWidth: '75%' }}
      >
        <Text className={`text-sm leading-5 ${isMe ? 'text-white' : 'text-text'}`}>
          {item.text}
        </Text>
        <Text className={`text-[10px] mt-1 ${isMe ? 'text-blue-100 text-right' : 'text-text-secondary'}`}>
          {formatTime(item.timestamp)}
        </Text>
      </View>
    </Animated.View>
  );
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [thinking, setThinking] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        setLoading(false);
        return;
      }
      getMessages()
        .then((data) => {
          const list = Array.isArray(data) ? data : data.data ?? [];
          const loaded = list.map((m: any) => ({
            id: m.id,
            from: 'me',
            text: m.body,
            timestamp: new Date(m.created_at),
          }));
          setMessages(loaded.reverse());
        })
        .catch((err) => console.error('Error cargando mensajes:', err))
        .finally(() => setLoading(false));
    });
  }, []);

  const sendMessage = async () => {
    if (!inputText.trim() || thinking) return;
    const text = inputText;
    setInputText('');

    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), from: 'me', text, timestamp: new Date() },
    ]);

    setThinking(true);
    try {
      const data = await apiSendMessage(text);
      const messageId = data.id;

      // Esperar 1 segundo antes de empezar el polling
      await new Promise(resolve => setTimeout(resolve, 10000));

      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const msgs = await getMessages();
        const list = Array.isArray(msgs) ? msgs : msgs.data ?? [];
        const msg = list.find((m: any) => m.id === messageId);
        console.warn(`Intento ${attempts}: messageId=${messageId}, msg=`, JSON.stringify(msg));
        if (msg?.response || attempts > 10) {
          clearInterval(poll);
          if (msg?.response) {
            setMessages((prev) => [
              ...prev,
              {
                id: messageId + '_bot',
                from: 'bot',
                text: msg.response,
                timestamp: new Date(),
              },
            ]);
          }
          setThinking(false);
        }
      }, 1500);
    } catch (err) {
      console.error('Error enviando mensaje:', err);
      setThinking(false);
    }
  };

  return (
    <View className="flex-1 bg-bg">
      {/* Header */}
      <SafeAreaView edges={['top']} className="bg-bg-secondary">
        <View className="flex-row items-center justify-between px-5 py-3 border-b border-border">
          <View className="flex-row items-center gap-3">
            <View className="relative">
              <View className="w-12 h-12 rounded-full bg-bg-secondary items-center justify-center border-2 border-primary">
                <Text className="text-2xl">🤖</Text>
              </View>
              <View className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-green-400 border-2 border-bg" />
            </View>
            <View>
              <Text className="text-text text-base font-bold tracking-wide">CanoBot</Text>
              <Text className={`${STYLES.text.secondary} text-xs`}>
                {thinking ? '✦ Procesando...' : 'Asistente de Domótica'}
              </Text>
            </View>
          </View>
          {/* Signal bars */}
          <View className="flex-row items-end gap-0.5">
            <View className="w-1 h-1.5 rounded-sm bg-primary" />
            <View className="w-1 h-2.5 rounded-sm bg-primary" />
            <View className="w-1 h-3.5 rounded-sm bg-primary" />
          </View>
        </View>
      </SafeAreaView>

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {loading ? (
          <View className="flex-1 items-center justify-center gap-3">
            <ActivityIndicator size="large" color="#3B82F6" />
            <Text className={`${STYLES.text.secondary} text-sm`}>Cargando historial...</Text>
          </View>
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
            ListEmptyComponent={
              <View className="flex-1 items-center justify-center pt-20 gap-2">
                <Text className="text-5xl">💬</Text>
                <Text className="text-text text-lg font-semibold">Sin mensajes aún</Text>
                <Text className={`${STYLES.text.secondary} text-sm`}>Envía un comando a CanoBot</Text>
              </View>
            }
            ListFooterComponent={
              thinking ? (
                <View className="flex-row items-end gap-2 my-1 px-4">
                  <View className="w-8 h-8 rounded-full bg-bg-secondary items-center justify-center border border-border">
                    <Text className="text-sm">🤖</Text>
                  </View>
                  <View className="bg-bg-secondary rounded-2xl rounded-bl-sm border border-border px-4 py-3">
                    <View className="flex-row gap-1 items-center">
                      <ThinkingDot delay={0} />
                      <ThinkingDot delay={200} />
                      <ThinkingDot delay={400} />
                    </View>
                  </View>
                </View>
              ) : null
            }
            renderItem={({ item }) => <MessageBubble item={item} />}
          />
        )}

        {/* Input bar */}
        <SafeAreaView edges={['bottom']} className="bg-bg-secondary">
          <View className="flex-row items-center px-4 py-3 border-t border-border gap-3">
            <TextInput
              className="flex-1 bg-bg rounded-3xl px-5 py-3 text-sm text-text border border-border"
              value={inputText}
              onChangeText={setInputText}
              placeholder="Escribe un comando..."
              placeholderTextColor="#94a3b8"
              onSubmitEditing={sendMessage}
              returnKeyType="send"
              editable={!thinking}
            />
            <TouchableOpacity
              className={`w-12 h-12 rounded-full items-center justify-center ${
                thinking ? 'bg-bg-secondary' : 'bg-primary'
              }`}
              onPress={sendMessage}
              activeOpacity={0.7}
              disabled={thinking}
            >
              <Text className="text-white text-base">➤</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  listContent: { paddingHorizontal: 16, paddingVertical: 16, flexGrow: 1 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#3B82F6' },
});