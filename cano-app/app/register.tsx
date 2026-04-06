import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { supabase } from '../api/supabase';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

export default function RegisterScreen() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    if (!username || !email || !password || !confirmPassword) {
      setError('Rellena todos los campos');
      return;
    }
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/users/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Error al registrar');
      }

      const { error: loginError } = await supabase.auth.signInWithPassword({ email, password });
      if (loginError) throw new Error(loginError.message);

    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-slate-900">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          className="flex-1"
          contentContainerClassName="px-8 py-12 gap-8"
          keyboardShouldPersistTaps="handled"
        >
          {/* Header */}
          <View className="items-center gap-3">
            <View className="w-20 h-20 rounded-full bg-slate-800 border-2 border-indigo-500 items-center justify-center">
              <Text className="text-4xl">🤖</Text>
            </View>
            <Text className="text-white text-3xl font-bold tracking-wide">Crear cuenta</Text>
            <Text className="text-slate-400 text-sm">Únete a CanoBot</Text>
          </View>

          {/* Form */}
          <View className="gap-4">
            <View className="gap-1.5">
              <Text className="text-slate-400 text-xs uppercase tracking-widest">Usuario</Text>
              <TextInput
                className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3.5 text-slate-100 text-sm"
                value={username}
                onChangeText={setUsername}
                placeholder="tunombre"
                placeholderTextColor="#475569"
                autoCapitalize="none"
              />
            </View>

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

            <View className="gap-1.5">
              <Text className="text-slate-400 text-xs uppercase tracking-widest">Confirmar contraseña</Text>
              <TextInput
                className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3.5 text-slate-100 text-sm"
                value={confirmPassword}
                onChangeText={setConfirmPassword}
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
              onPress={handleRegister}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading
                ? <ActivityIndicator color="white" />
                : <Text className="text-white font-semibold text-sm tracking-wide">Crear cuenta</Text>
              }
            </TouchableOpacity>
          </View>

          {/* Footer */}
          <View className="flex-row justify-center gap-1">
            <Text className="text-slate-500 text-sm">¿Ya tienes cuenta?</Text>
            <TouchableOpacity onPress={() => router.back()}>
              <Text className="text-indigo-400 text-sm font-semibold">Inicia sesión</Text>
            </TouchableOpacity>
          </View>

        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}