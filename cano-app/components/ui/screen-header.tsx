import { Text, View } from 'react-native';
import { STYLES } from '@/constants/styles';

type Props = {
  title: string;
  subtitle?: string;
};

export function ScreenHeader({ title, subtitle }: Readonly<Props>) {
  return (
    <View className="mb-8">
      <Text className={STYLES.headers.mainTitle}>{title}</Text>
      {subtitle && (
        <Text className={STYLES.headers.subtitle}>{subtitle}</Text>
      )}
    </View>
  );
}