import { Ionicons } from '@expo/vector-icons';
import { Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

type ChatHeaderProps = {
  thinking: boolean;
  onHistoryPress: () => void;
};

export function ChatHeader({ thinking, onHistoryPress }: ChatHeaderProps) {
  return (
    <SafeAreaView edges={['top']} className="bg-bg-secondary">
      <View className="flex-row items-center justify-between px-5 py-3 border-b border-border">
        <View className="flex-row items-center gap-3 flex-1">
          <View className="relative">
            <View className="w-12 h-12 rounded-full bg-bg-secondary items-center justify-center border-2 border-primary">
              <Ionicons name="chatbubble" size={24} color="#3B82F6" />
            </View>
            {!thinking && (
              <View className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-green-400 border-2 border-bg" />
            )}
          </View>
          <View>
            <Text className="text-text text-base font-bold tracking-wide">CanoBot</Text>
            <Text className="text-text-secondary text-xs">
              {thinking ? 'Procesando...' : 'Asistente de domótica'}
            </Text>
          </View>
        </View>

        {/* Botón historial */}
        <TouchableOpacity
          onPress={onHistoryPress}
          className="w-10 h-10 rounded-lg bg-bg items-center justify-center border border-border"
          activeOpacity={0.7}
        >
          <Ionicons name="menu" size={20} color="#3B82F6" />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
