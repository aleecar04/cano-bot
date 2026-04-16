import { Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type Props = {
  title: string;
  subtitle: string;
};

export function AuthHeader({ title, subtitle }: Props) {
  return (
    <View className="items-center gap-3">
      <View className="w-20 h-20 rounded-full bg-bg-secondary border-2 border-primary items-center justify-center">
        <Ionicons name="chatbubble" size={40} color="#3B82F6" />
      </View>
      <Text className="text-text text-3xl font-bold tracking-wide">{title}</Text>
      <Text className="text-text-secondary text-sm">{subtitle}</Text>
    </View>
  );
}