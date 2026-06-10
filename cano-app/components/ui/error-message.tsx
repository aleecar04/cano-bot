import { Text, View } from 'react-native';

type Props = {
  message: string | null;
};

export function ErrorMessage({ message }: Readonly<Props>) {
  if (!message) return null;
  return (
    <View className="bg-red-500 rounded-xl px-4 py-3">
      <Text className="text-white text-sm font-semibold">{message}</Text>
    </View>
  );
}