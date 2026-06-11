import { Image, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useUserProfile } from '@/context/user-profile';

function Avatar({ name }: Readonly<{ name: string }>) {
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');

  return (
    <View
      className="w-9 h-9 rounded-full bg-primary/20 border border-primary/30 items-center justify-center"
    >
      <Text className="text-primary font-bold text-sm">{initials || '?'}</Text>
    </View>
  );
}

export function AppHeader() {
  const router  = useRouter();
  const { profile } = useUserProfile();

  const displayName = [profile?.first_name, profile?.last_name].filter(Boolean).join(' ')
    || profile?.username
    || '';

  return (
    <SafeAreaView edges={['top']} className="bg-bg border-b border-border">
      <View className="flex-row items-center justify-between px-4 py-2.5">

        {/* Brand */}
        <View className="flex-row items-center gap-2">
          <Image
            source={require('../../assets/images/cano.png')}
            resizeMode="contain"
            style={{ width: 28, height: 28 }}
          />
          <Text className="text-text font-bold text-lg tracking-tight">Cano-bot</Text>
        </View>

        {/* Avatar → perfil */}
        <TouchableOpacity
          onPress={() => router.push('/profile')}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Abrir perfil"
        >
          <Avatar name={displayName} />
        </TouchableOpacity>

      </View>
    </SafeAreaView>
  );
}
