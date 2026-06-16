import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { deviceIcon, deviceColor } from '@/utils/device-icons';

interface Accion {
  action: string;
  desc: string;
}

interface Grupo {
  label: string;
  acciones: Accion[];
}

interface BotActionsListProps {
  device?: string;
  device_type?: string;
  label?: string;
  acciones?: Accion[];
  grupos?: Grupo[];
}

function ActionChips({ acciones }: Readonly<{ acciones: Accion[] }>) {
  return (
    <View className="flex-row flex-wrap gap-2 mt-2">
      {acciones.map((a) => (
        <View key={a.action} className="bg-bg border border-border rounded-lg px-3 py-1.5">
          <Text className="text-text-secondary text-xs font-medium">{a.desc}</Text>
        </View>
      ))}
    </View>
  );
}

export function BotActionsList({ device, device_type, label, acciones, grupos }: Readonly<BotActionsListProps>) {
  // Caso: todas las acciones agrupadas por tipo de dispositivo.
  if (grupos && grupos.length > 0) {
    return (
      <View className="bg-bg-secondary border border-border rounded-2xl p-4 gap-3" style={{ maxWidth: '88%' }}>
        <Text className="text-text font-bold text-sm">Acciones por tipo de dispositivo</Text>
        {grupos.map((g) => (
          <View key={g.label}>
            <Text className="text-text-secondary text-xs font-semibold uppercase tracking-wider">{g.label}</Text>
            <ActionChips acciones={g.acciones} />
          </View>
        ))}
      </View>
    );
  }

  // Caso: acciones de un dispositivo concreto.
  const color = deviceColor(device_type ?? '');
  return (
    <View className="bg-bg-secondary border border-border rounded-2xl p-4" style={{ maxWidth: '88%' }}>
      <View className="flex-row items-center gap-2">
        <View
          style={{ backgroundColor: `${color}20` }}
          className="w-8 h-8 rounded-lg items-center justify-center"
        >
          <Ionicons name={deviceIcon(device_type ?? '') as any} size={16} color={color} />
        </View>
        <View>
          <Text className="text-text font-bold text-sm">{device}</Text>
          {!!label && <Text className="text-text-secondary text-xs">{label}</Text>}
        </View>
      </View>
      {!!acciones && acciones.length > 0 && <ActionChips acciones={acciones} />}
    </View>
  );
}
