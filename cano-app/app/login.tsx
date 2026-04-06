import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { supabase } from '../api/supabase';

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    if (!email || !password) {
      setError('Rellena todos los campos');
      return;
    }
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setError(error.message);

    setLoading(false);
  };

  return (
    <SafeAreaView className="flex-1 bg-slate-900">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View className="flex-1 px-8 justify-center gap-8">

          {/* Header */}
          <View className="items-center gap-3">
            <View className="w-20 h-20 rounded-full bg-slate-800 border-2 border-indigo-500 items-center justify-center">
              <Text className="text-4xl">🤖</Text>
            </View>
            <Text className="text-white text-3xl font-bold tracking-wide">CanoBot</Text>
            <Text className="text-slate-400 text-sm">Asistente de Domótica</Text>
          </View>

          {/* Form */}
          <View className="gap-4">
            <View className="gap-1.5">
              <Text className="text-slate-400 text-xs uppercase tracking-widest">Email</Text>
              <TextInput
                className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3.5 text-slate-100 text-sm"
                value={email}
                onChangeText={setEmail}
                placeholder="tu@email.com"
                placeholderTextColor="#475569"
                autoCapitalize="none"
                keyboardType="email-address"
              />
            </View>

            <View className="gap-1.5">
              <Text className="text-slate-400 text-xs uppercase tracking-widest">Contraseña</Text>
              <TextInput
                className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3.5 text-slate-100 text-sm"
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                placeholderTextColor="#475569"
                secureTextEntry
              />
            </View>

            {error && (
              <View className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
                <Text className="text-red-400 text-sm">{error}</Text>
              </View>
            )}

            <TouchableOpacity
              className={`rounded-xl py-4 items-center mt-2 ${loading ? 'bg-indigo-500/50' : 'bg-indigo-500'}`}
              onPress={handleLogin}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading
                ? <ActivityIndicator color="white" />
                : <Text className="text-white font-semibold text-sm tracking-wide">Iniciar sesión</Text>
              }
            </TouchableOpacity>
          </View>

          {/* Footer */}
          <View className="flex-row justify-center gap-1">
            <Text className="text-slate-500 text-sm">¿No tienes cuenta?</Text>
            <TouchableOpacity onPress={() => router.push('/register' as any)}>
              <Text className="text-indigo-400 text-sm font-semibold">Regístrate</Text>
            </TouchableOpacity>
          </View>

        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}