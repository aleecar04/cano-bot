import { useState } from 'react';
import {
  View, Text, TouchableOpacity, TextInput,
  ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { joinHouse, setupHouse, generateBotSetup, type GeneratedBotCredentials } from '@/api/houses';
import { useUserProfile } from '@/context/user-profile';
import { ONBOARDING_DONE_KEY } from './onboarding';

type Mode = null | 'owner' | 'member';
type OwnerSubMode = 'manual' | 'generate';

export default function HouseSetupScreen() {
  const router = useRouter();
  const { profile } = useUserProfile();

  const [mode, setMode]               = useState<Mode>(null);
  const [ownerSub, setOwnerSub]       = useState<OwnerSubMode>('generate');
  const [code, setCode]               = useState('');
  const [botJid, setBotJid]           = useState('');
  const [joining, setJoining]         = useState(false);
  const [claiming, setClaiming]       = useState(false);
  const [generating, setGenerating]   = useState(false);
  const [credentials, setCredentials] = useState<GeneratedBotCredentials | null>(null);
  const [error, setError]             = useState<string | null>(null);

  const handleClaim = async () => {
    const jid = botJid.trim().toLowerCase();
    if (!jid) { setError('Introduce el JID del bot'); return; }
    setClaiming(true);
    setError(null);
    try {
      await setupHouse(jid);
      await AsyncStorage.setItem(ONBOARDING_DONE_KEY, 'true');
      router.replace('/(tabs)');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al configurar la casa');
    } finally {
      setClaiming(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const creds = await generateBotSetup();
      setCredentials(creds);
      await AsyncStorage.setItem(ONBOARDING_DONE_KEY, 'true');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error generando credenciales');
    } finally {
      setGenerating(false);
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
      // Mark onboarding as done so we skip it and go directly home
      await AsyncStorage.setItem(ONBOARDING_DONE_KEY, 'true');
      router.replace('/(tabs)');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al unirse al hogar';
      setError(msg);
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
                  <Text className="text-text-secondary text-xs">Configuro el bot del hogar</Text>
                </View>
                {mode === 'owner' && (
                  <Ionicons name="checkmark-circle" size={20} color="#3B82F6" />
                )}
              </View>
              <Text className="text-text-secondary text-xs leading-4">
                Ejecuta el script de configuración del bot y gestiona el hogar como administrador.
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

            {/* OWNER */}
            {mode === 'owner' && (
              <View className="gap-4">

                {/* Sub-mode selector */}
                <View className="flex-row gap-3">
                  {([
                    { key: 'generate', label: 'Generar bot nuevo', icon: 'sparkles-outline' },
                    { key: 'manual',   label: 'Ya tengo un bot',   icon: 'key-outline' },
                  ] as const).map(({ key, label, icon }) => (
                    <TouchableOpacity
                      key={key}
                      onPress={() => { setOwnerSub(key); setError(null); setCredentials(null); }}
                      activeOpacity={0.8}
                      className={`flex-1 rounded-xl border p-3 items-center gap-1.5 ${ownerSub === key ? 'bg-primary/10 border-primary' : 'bg-bg-secondary border-border'}`}
                    >
                      <Ionicons name={icon} size={20} color={ownerSub === key ? '#3B82F6' : '#64748b'} />
                      <Text className={`text-xs font-semibold text-center ${ownerSub === key ? 'text-primary' : 'text-text-secondary'}`}>{label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                {/* ── Generar bot nuevo ── */}
                {ownerSub === 'generate' && !credentials && (
                  <View className="gap-4">
                    <View className="bg-bg-secondary border border-border rounded-2xl p-5">
                      <Text className="text-text font-bold text-sm mb-2">¿Cómo funciona?</Text>
                      <Text className="text-text-secondary text-xs leading-5">
                        Se generará automáticamente una cuenta XMPP para tu bot y se creará tu casa.
                        Recibirás el JID y la contraseña del bot — guárdalos para configurar errbot.
                      </Text>
                    </View>

                    {error && (
                      <View className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                        <Text className="text-red-400 text-sm text-center">{error}</Text>
                      </View>
                    )}

                    <TouchableOpacity
                      className={`rounded-2xl py-4 items-center flex-row justify-center gap-2 ${generating ? 'bg-primary/40' : 'bg-primary'}`}
                      onPress={handleGenerate}
                      disabled={generating}
                      activeOpacity={0.8}
                    >
                      {generating
                        ? <ActivityIndicator color="white" />
                        : <Ionicons name="sparkles-outline" size={18} color="white" />
                      }
                      <Text className="text-white font-semibold text-base">
                        {generating ? 'Generando...' : 'Generar credenciales'}
                      </Text>
                    </TouchableOpacity>
                  </View>
                )}

                {/* ── Credenciales generadas — mostrar una sola vez ── */}
                {ownerSub === 'generate' && credentials && (
                  <View className="gap-4">
                    <View className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex-row items-start gap-2">
                      <Ionicons name="warning-outline" size={16} color="#f59e0b" style={{ marginTop: 1 }} />
                      <Text className="text-amber-400 text-xs leading-5 flex-1">
                        Estas credenciales solo se muestran una vez. Guárdalas ahora para configurar errbot.
                      </Text>
                    </View>

                    <View className="bg-bg-secondary border border-border rounded-2xl p-5 gap-4">
                      <View>
                        <Text className="text-text-secondary text-xs font-semibold mb-1.5">JID del bot</Text>
                        <View className="bg-bg border border-border rounded-xl px-4 py-3">
                          <Text className="text-text font-mono text-sm" selectable>{credentials.jid}</Text>
                        </View>
                      </View>
                      <View>
                        <Text className="text-text-secondary text-xs font-semibold mb-1.5">Contraseña</Text>
                        <View className="bg-bg border border-border rounded-xl px-4 py-3">
                          <Text className="text-text font-mono text-sm" selectable>{credentials.password}</Text>
                        </View>
                      </View>
                      <View className="bg-bg border border-border rounded-xl px-4 py-3">
                        <Text className="text-text-secondary text-xs leading-4">
                          Usa estos datos al ejecutar <Text className="font-mono text-indigo-400">bash setup-bot.sh</Text> o al configurar errbot manualmente.
                        </Text>
                      </View>
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

                {/* ── Ya tengo un bot (manual) ── */}
                {ownerSub === 'manual' && (
                  <View className="gap-4">
                    <View className="bg-bg-secondary border border-border rounded-2xl p-5 gap-3">
                      <Text className="text-text font-bold text-sm">JID del bot</Text>
                      <Text className="text-text-secondary text-xs">
                        Introdúcelo tal como aparece en la configuración (ej: cano-bot@tuservidor.com)
                      </Text>
                      <TextInput
                        className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm"
                        value={botJid}
                        onChangeText={(t) => { setBotJid(t); setError(null); }}
                        placeholder="cano-bot@tuservidor.com"
                        placeholderTextColor="#475569"
                        autoCapitalize="none"
                        autoCorrect={false}
                        editable={!claiming}
                      />
                    </View>

                    {error && (
                      <View className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                        <Text className="text-red-400 text-sm text-center">{error}</Text>
                      </View>
                    )}

                    <TouchableOpacity
                      className={`rounded-2xl py-4 items-center ${botJid.trim() && !claiming ? 'bg-primary' : 'bg-primary/40'}`}
                      onPress={handleClaim}
                      disabled={!botJid.trim() || claiming}
                      activeOpacity={0.8}
                    >
                      {claiming
                        ? <ActivityIndicator color="white" />
                        : <Text className="text-white font-semibold text-base">Vincular casa</Text>
                      }
                    </TouchableOpacity>
                  </View>
                )}

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
