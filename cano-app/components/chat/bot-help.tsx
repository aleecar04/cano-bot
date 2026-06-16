import { View, Text } from 'react-native';

interface Seccion {
  titulo: string;
  items: string[];
}

interface BotHelpProps {
  secciones: Seccion[];
}

export function BotHelp({ secciones }: Readonly<BotHelpProps>) {
  return (
    <View className="gap-2" style={{ maxWidth: '88%' }}>
      {secciones.map((s) => (
        <View key={s.titulo} className="bg-bg-secondary border border-border rounded-2xl p-3">
          <Text className="text-text font-bold text-sm mb-1">{s.titulo}</Text>
          {s.items.map((item) => (
            <Text key={item} className="text-text-secondary text-xs leading-5">
              {'•'} {item}
            </Text>
          ))}
        </View>
      ))}
    </View>
  );
}
