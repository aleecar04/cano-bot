import { Text, View } from 'react-native';
import { STYLES } from '@/constants/styles';

type InfoRow = {
  label: string;
  value: string;
};

type Props = {
  title: string;
  rows: InfoRow[];
};

export function ProfileInfoCard({ title, rows }: Readonly<Props>) {
  return (
    <View className={`${STYLES.cards.light} mb-8`}>
      <Text className={`${STYLES.headers.sectionTitle}`}>{title}</Text>
      <View className="gap-5">
        {rows.map((row, i) => (
          <View key={row.label}>
            {i > 0 && <View className="border-t border-border mb-5" />}
            <Text className="text-text-secondary text-xs mb-1.5">{row.label}</Text>
            <Text className="text-text text-base font-semibold">{row.value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}