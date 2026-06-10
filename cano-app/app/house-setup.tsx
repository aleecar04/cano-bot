import { useState } from 'react';
import {
  View, Text, TouchableOpacity, TextInput,
  ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { joinHouse, setupHouse } from '@/api/houses';

type Mode = null | 'owner' | 'member';

export default function HouseSetupScreen() {
  const router = useRouter();

  const [mode, setMode]         = useState<Mode>(null);
  const [houseName, setHouseName] = useState('');
  const [code, setCode]         = useState('');
  const [joining, setJoining]   = useState(false);
  const [creating, setCreating] = useState(false);
  const [botToken, setBotToken] = useState<string | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const { bot_token } = await setupHouse(houseName.trim() || undefined);
      setBotToken(bot_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error creando la casa');
    } finally {
      setCreating(false);
    }
  };

  const handleJoin = async () => {
    const trimmed = code.trim().toUpperCase();
    if (trimmed.length !== 6) {
      setError('El código debe tener exactamente 6 caracteres');
      return;
    }
    setJoining(true);
    setError(null);
    try {
      await joinHouse(trimmed);
      router.replace('/(tabs)');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al unirse al hogar');
    } finally {
      setJoining(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ flexGrow: 1 }}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Header */}
          <View className="px-6 pt-8 pb-6">
            <View className="w-14 h-14 rounded-2xl bg-primary/10 items-center justify-center mb-4">
              <Ionicons name="home" size={28} color="#3B82F6" />
            </View>
            <Text className="text-text text-3xl font-black">Configura tu hogar</Text>
            <Text className="text-text-secondary text-sm mt-2 leading-5">
              Para continuar, elige una de las siguientes opciones.
            </Text>
          </View>

          {/* Option cards */}
          <View className="px-6 gap-4">

            {/* Owner card */}
            <TouchableOpacity
              onPress={() => { setMode('owner'); setError(null); }}
              activeOpacity={0.8}
              className={`rounded-2xl border p-5 ${
                mode === 'owner'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-bg-secondary border-border'
              }`}
            >
              <View className="flex-row items-center gap-3 mb-2">
                <View className={`w-10 h-10 rounded-xl items-center justify-center ${
                  mode === 'owner' ? 'bg-primary' : 'bg-bg'
                }`}>
                  <Ionicons name="settings-outline" size={20} color="white" />
                </View>
                <View className="flex-1">
                  <Text className="text-text font-bold text-base">Soy el propietario</Text>
                  <Text className="text-text-secondary text-xs">Creo el hogar y configuro el bot</Text>
                </View>
                {mode === 'owner' && (
                  <Ionicons name="checkmark-circle" size={20} color="#3B82F6" />
                )}
              </View>
              <Text className="text-text-secondary text-xs leading-4">
                Creas tu casa y obtienes el token para configurar el bot que corre en tu red local.
              </Text>
            </TouchableOpacity>

            {/* Member card */}
            <TouchableOpacity
              onPress={() => { setMode('member'); setError(null); }}
              activeOpacity={0.8}
              className={`rounded-2xl border p-5 ${
                mode === 'member'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-bg-secondary border-border'
              }`}
            >
              <View className="flex-row items-center gap-3 mb-2">
                <View className={`w-10 h-10 rounded-xl items-center justify-center ${
                  mode === 'member' ? 'bg-primary' : 'bg-bg'
                }`}>
                  <Ionicons name="people-outline" size={20} color="white" />
                </View>
                <View className="flex-1">
                  <Text className="text-text font-bold text-base">Tengo un código</Text>
                  <Text className="text-text-secondary text-xs">Me han invitado a un hogar</Text>
                </View>
                {mode === 'member' && (
                  <Ionicons name="checkmark-circle" size={20} color="#3B82F6" />
                )}
              </View>
              <Text className="text-text-secondary text-xs leading-4">
                Introduce el código de invitación de 6 caracteres que te ha enviado el propietario.
              </Text>
            </TouchableOpacity>
          </View>

          {/* Conditional content */}
          <View className="px-6 mt-6">

            {/* OWNER — create house, then show bot_token once */}
            {mode === 'owner' && !botToken && (
              <View className="gap-4">
                <View className="bg-bg-secondary border border-border rounded-2xl p-5 gap-3">
                  <Text className="text-text font-bold text-sm">Nombre de la casa (opcional)</Text>
                  <TextInput
                    className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm"
                    style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
                    value={houseName}
                    onChangeText={(t) => { setHouseName(t); setError(null); }}
                    placeholder="Mi Casa"
                    placeholderTextColor="#475569"
                    editable={!creating}
                    maxLength={50}
                  />
                  <Text className="text-text-secondary text-xs leading-5">
                    Al crear la casa obtendrás un token único. Cópialo en tu bot (variable BOT_TOKEN).
                  </Text>
                </View>

                {error && (
                  <View className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                    <Text className="text-red-400 text-sm text-center">{error}</Text>
                  </View>
                )}

                <TouchableOpacity
                  className={`rounded-2xl py-4 items-center flex-row justify-center gap-2 ${creating ? 'bg-primary/40' : 'bg-primary'}`}
                  onPress={handleCreate}
                  disabled={creating}
                  activeOpacity={0.8}
                >
                  {creating
                    ? <ActivityIndicator color="white" />
                    : <Ionicons name="add-circle-outline" size={18} color="white" />
                  }
                  <Text className="text-white font-semibold text-base">
                    {creating ? 'Creando...' : 'Crear casa'}
                  </Text>
                </TouchableOpacity>
              </View>
            )}

            {/* OWNER — token shown once */}
            {mode === 'owner' && botToken && (
              <View className="gap-4">
                <View className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex-row items-start gap-2">
                  <Ionicons name="warning-outline" size={16} color="#f59e0b" style={{ marginTop: 1 }} />
                  <Text className="text-amber-400 text-xs leading-5 flex-1">
                    Este token solo se muestra una vez. Cópialo ahora; si lo pierdes, deberás
                    regenerarlo desde el perfil de tu casa.
                  </Text>
                </View>

                <View className="bg-bg-secondary border border-border rounded-2xl p-5 gap-3">
                  <Text className="text-text-secondary text-xs font-semibold">Token del bot (BOT_TOKEN)</Text>
                  <View className="bg-bg border border-border rounded-xl px-4 py-3">
                    <Text className="text-text font-mono text-sm" selectable>{botToken}</Text>
                  </View>
                  <Text className="text-text-secondary text-xs leading-4">
                    Pégalo al ejecutar <Text className="font-mono text-indigo-400">bash setup-bot.sh</Text> o
                    en la variable <Text className="font-mono text-indigo-400">BOT_TOKEN</Text> del archivo .bot.env del bot.
                  </Text>
                </View>

                <TouchableOpacity
                  className="rounded-2xl py-4 items-center bg-green-600"
                  onPress={() => router.replace('/(tabs)')}
                  activeOpacity={0.8}
                >
                  <Text className="text-white font-semibold text-base">Ya lo he guardado — Continuar</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* MEMBER — join with code */}
            {mode === 'member' && (
              <View className="gap-4">
                <View className="bg-bg-secondary border border-border rounded-2xl p-5">
                  <Text className="text-text font-bold text-sm mb-1">Código de invitación</Text>
                  <Text className="text-text-secondary text-xs mb-4">
                    Introduce el código de 6 caracteres que te han enviado.
                  </Text>
                  <TextInput
                    className="bg-bg border border-border rounded-xl px-4 py-4 text-text text-2xl font-bold tracking-widest text-center"
                    value={code}
                    onChangeText={(t) => {
                      setCode(t.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6));
                      setError(null);
                    }}
                    placeholder="ABC123"
                    placeholderTextColor="#475569"
                    autoCapitalize="characters"
                    autoCorrect={false}
                    maxLength={6}
                    editable={!joining}
                  />
                </View>

                {error && (
                  <View className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                    <Text className="text-red-400 text-sm text-center">{error}</Text>
                  </View>
                )}

                <TouchableOpacity
                  className={`rounded-2xl py-4 items-center ${
                    code.length === 6 && !joining ? 'bg-primary' : 'bg-primary/40'
                  }`}
                  onPress={handleJoin}
                  disabled={code.length !== 6 || joining}
                  activeOpacity={0.8}
                >
                  {joining ? (
                    <ActivityIndicator color="white" />
                  ) : (
                    <Text className="text-text font-semibold text-base">Unirme al hogar</Text>
                  )}
                </TouchableOpacity>
              </View>
            )}

          </View>

          <View className="h-8" />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
