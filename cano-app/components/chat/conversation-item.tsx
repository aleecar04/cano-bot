import { TouchableOpacity, View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export type Conversation = {
  id: string;
  title: string;
  updated_at: string;
};

export function ConversationItem({
  item,
  onPress,
}: Readonly<{
  item: Conversation;
  onPress: (id: string) => void;
}>) {
  const date = new Date(item.updated_at);
  const formatted = date.toLocaleDateString([], {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });

  return (
    <TouchableOpacity
      className="flex-row items-center px-4 py-4 border-b border-border gap-3"
      onPress={() => onPress(item.id)}
      activeOpacity={0.7}
    >
      <View className="w-10 h-10 rounded-full bg-bg-secondary items-center justify-center border border-border">
        <Ionicons name="chatbubbles" size={16} color="#3B82F6" />
      </View>
      <View className="flex-1">
        <Text className="text-text text-sm font-semibold" numberOfLines={1}>
          {item.title}
        </Text>
        <Text className="text-text-secondary text-xs mt-0.5">{formatted}</Text>
      </View>
      <Text className="text-text-secondary text-lg">›</Text>
    </TouchableOpacity>
  );
}