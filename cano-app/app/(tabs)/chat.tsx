import { useEffect, useRef, useState } from 'react';
import {
  View, TextInput, FlatList, Text,
  TouchableOpacity, KeyboardAvoidingView, Platform,
  ActivityIndicator, Modal, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { friendlyError } from '@/utils/friendly-error';
import {
  sendMessage as apiSendMessage,
  getConversationMessages,
  createConversation,
  getConversations,
} from '../../api/conversations';
import { supabase } from '../../api/supabase';
import { STYLES } from '../../constants/styles';
import { MessageBubble, type Message } from '@/components/chat/message-bubble';
import { BotJsonBubble } from '@/components/chat/bot-json-bubble';
import { ThinkingDots } from '@/components/chat/thinking-dots';
import { ConversationItem, type Conversation } from '@/components/chat/conversation-item';

const storageKey = (userId: string) => `@cano4/active_conv_${userId}`;
const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 15;

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [thinking, setThinking] = useState(false);
  const [historialVisible, setHistorialVisible] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const flatListRef = useRef<FlatList>(null);
  const persistedConvId = useRef<string | undefined>(undefined);
  const userStorageKey = useRef<string>('');

  useEffect(() => {
    const initChat = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { setLoading(false); return; }

      // Key is scoped to this user — no cross-user contamination
      userStorageKey.current = storageKey(session.user.id);

      try {
        const savedId = await AsyncStorage.getItem(userStorageKey.current);
        if (savedId) {
          try {
            const msgs = await getConversationMessages(savedId);
            persistedConvId.current = savedId;
            setMessages(_mapMessagesToUI(msgs));
          } catch {
            await AsyncStorage.removeItem(userStorageKey.current);
          }
        }
      } catch (err) {
        console.error('initChat error', err);
      } finally {
        setLoading(false);
      }
    };
    initChat();
  }, []);

  const openHistorial = async () => {
    try {
      const convs = await getConversations();
      // Ensure title is always a string to match ConversationItem's type
      setConversations(convs.map((c) => ({ ...c, title: c.title ?? 'Sin título' })));
    } catch (err) {
      console.error('getConversations error', err);
    }
    setHistorialVisible(true);
  };

  const selectConversation = async (id: string) => {
    setHistorialVisible(false);
    persistedConvId.current = id;
    await AsyncStorage.setItem(userStorageKey.current, id);
    try {
      const msgs = await getConversationMessages(id);
      setMessages(_mapMessagesToUI(msgs));
    } catch (err) {
      console.error('selectConversation error', err);
    }
  };

  const startNewConversation = () => {
    // Discard current session conversation (local only — not persisted until first message)
    persistedConvId.current = undefined;
    setMessages([]);
    AsyncStorage.removeItem(userStorageKey.current);
    setHistorialVisible(false);
  };

  const sendMessage = async () => {
    if (!inputText.trim() || thinking) return;
    const text = inputText.trim();
    setInputText('');
    setThinking(true);

    try {
      // Ensure we have a persisted conversation before sending
      if (!persistedConvId.current) {
        const newConv = await createConversation(text.slice(0, 60));
        persistedConvId.current = newConv.id;
        await AsyncStorage.setItem(userStorageKey.current, persistedConvId.current);
      }
      let activeId = persistedConvId.current;

      // Optimistic UI update
      setMessages((prev) => [
        ...prev,
        { id: `local-${Date.now()}`, from: 'me', text, timestamp: new Date() },
      ]);

      let data;
      try {
        data = await apiSendMessage(text, activeId);
      } catch (err) {
        // Stale conversation (404) — create a fresh one and retry once
        if (String(err).includes('Conversation not found') || String(err).includes('404')) {
          persistedConvId.current = undefined;
          await AsyncStorage.removeItem(userStorageKey.current);
          const newConv = await createConversation(text.slice(0, 60));
          persistedConvId.current = newConv.id;
          activeId = newConv.id;
          await AsyncStorage.setItem(userStorageKey.current, persistedConvId.current);
          data = await apiSendMessage(text, activeId);
        } else {
          throw err;
        }
      }
      const messageId: string = data.id;

      // Poll until the bot responds or we time out
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const msgs = await getConversationMessages(activeId);
          const msg = msgs.find((m: any) => m.id === messageId);
          if (msg?.response || attempts >= MAX_POLL_ATTEMPTS) {
            clearInterval(poll);
            const botResponse = msg?.response ?? null;
            if (botResponse) {
              setMessages((prev) => [
                ...prev,
                {
                  id: `${messageId}_bot`,
                  from: 'bot' as const,
                  text: botResponse,
                  timestamp: new Date(),
                },
              ]);
            }
            setThinking(false);
          }
        } catch {
          // Network error during poll — keep trying
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      Alert.alert('No se pudo enviar', friendlyError(err));
      setThinking(false);
    }
  };

  return (
    <View className="flex-1 bg-bg">
      <SafeAreaView edges={['top']} className="bg-bg">
        <TouchableOpacity
          onPress={openHistorial}
          className="self-end mr-4 mt-2 p-2"
          activeOpacity={0.7}
        >
          <Ionicons name="ellipsis-vertical" size={24} color="#3B82F6" />
        </TouchableOpacity>
      </SafeAreaView>

      <Modal
        visible={historialVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setHistorialVisible(false)}
      >
        <View className="flex-1 bg-bg">
          <SafeAreaView edges={['top']} className="bg-bg-secondary border-b border-border">
            <View className="flex-row items-center justify-between px-5 py-4">
              <View className="flex-1">
                <Text className="text-text text-lg font-bold">Historial</Text>
                <Text className="text-text-secondary text-xs mt-1">
                  {conversations.length}{' '}
                  {conversations.length === 1 ? 'conversación' : 'conversaciones'}
                </Text>
              </View>
              <View className="flex-row gap-3 items-center">
                <TouchableOpacity
                  onPress={startNewConversation}
                  className="p-2"
                  activeOpacity={0.7}
                >
                  <Ionicons name="add-circle-outline" size={24} color="#3B82F6" />
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setHistorialVisible(false)}
                  className="p-2"
                  activeOpacity={0.7}
                >
                  <Ionicons name="close" size={24} color="#3B82F6" />
                </TouchableOpacity>
              </View>
            </View>
          </SafeAreaView>

          <FlatList
            data={conversations}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ flexGrow: 1, paddingHorizontal: 12, paddingVertical: 12 }}
            ListEmptyComponent={
              <View className="flex-1 items-center justify-center gap-3">
                <Ionicons name="chatbubbles-outline" size={64} color="#94a3b8" />
                <Text className="text-text text-lg font-semibold">Sin conversaciones</Text>
              </View>
            }
            renderItem={({ item }) => (
              <ConversationItem item={item} onPress={selectConversation} />
            )}
          />
        </View>
      </Modal>

      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {loading ? (
          <View className="flex-1 items-center justify-center gap-3">
            <ActivityIndicator size="large" color="#3B82F6" />
            <Text className={`${STYLES.text.secondary} text-sm`}>Cargando...</Text>
          </View>
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id}
            contentContainerStyle={{ paddingVertical: 12, flexGrow: 1 }}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
            ListEmptyComponent={
              <View className="flex-1 items-center justify-center pt-20 gap-2">
                <Ionicons name="chatbubbles-outline" size={64} color="#94a3b8" />
                <Text className="text-text text-lg font-semibold">Sin mensajes aún</Text>
              </View>
            }
            ListFooterComponent={thinking ? <ThinkingDots /> : null}
            renderItem={({ item }) => {
              if (item.from === 'bot') {
                try {
                  const parsed = JSON.parse(item.text);
                  if (parsed && typeof parsed.tipo === 'string') {
                    return <BotJsonBubble data={parsed} timestamp={item.timestamp} />;
                  }
                } catch {
                  // Not JSON — fall through to normal bubble
                }
              }
              return <MessageBubble item={item} />;
            }}
          />
        )}

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
              className={`w-12 h-12 rounded-full items-center justify-center ${thinking ? 'bg-bg-secondary' : 'bg-primary'}`}
              onPress={sendMessage}
              activeOpacity={0.7}
              disabled={thinking}
            >
              <Ionicons name="send" size={20} color="white" />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </View>
  );
}

function _mapMessagesToUI(rawMessages: any[]): Message[] {
  return rawMessages.flatMap((m) => [
    { id: m.id, from: 'me' as const, text: m.body, timestamp: new Date(m.created_at) },
    ...(m.response
      ? [{ id: `${m.id}_bot`, from: 'bot' as const, text: m.response, timestamp: new Date(m.created_at) }]
      : []),
  ]);
}
