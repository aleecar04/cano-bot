import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Image, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export function AppHeader() {
  const router = useRouter();

  const goToProfile = () => {
    router.push('/profile');
  };

  return (
    <SafeAreaView edges={['top']} className="bg-blue-600">
      <View className="flex-row items-center justify-between px-4 py-4">
        {/* Icono de perfil a la izquierda */}
        <TouchableOpacity
          onPress={goToProfile}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Abrir perfil"
        >
          <Ionicons name="person-circle" size={32} color="white" />
        </TouchableOpacity>

        {/* Nombre y logo en el centro */}
        <View className="flex-row items-center justify-center flex-1 gap-2">
          <Text 
            className="text-blue-100 font-black"
            style={{ 
              fontSize: 24,
              fontStyle: 'italic',
              letterSpacing: 1.5,
              textShadowColor: 'rgba(0, 0, 0, 0.5)',
              textShadowOffset: { width: 2, height: 2 },
              textShadowRadius: 3,
            }}
          >
            Cano-Bot
          </Text>
          <Image
            source={require('../../assets/images/cano.png')}
            resizeMode="contain"
            style={{ width: 32, height: 32 }}
          />
        </View>

        {/* Espacio vacío a la derecha para balancear */}
        <View style={{ width: 32 }} />
      </View>
    </SafeAreaView>
  );
}
