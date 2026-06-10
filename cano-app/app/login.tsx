import { useState } from 'react';
import {
  View, Text, TouchableOpacity,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { supabase } from '../api/supabase';
import { AuthHeader } from '@/components/auth/auth-header';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

async function resolveIdentifier(identifier: string): Promise<string> {
  if (identifier.includes('@')) return identifier;
  const res = await fetch(`${API_URL}/api/v1/auth/resolve-username/${encodeURIComponent(identifier)}`);
  if (!res.ok) throw new Error('Usuario no encontrado');
  const data = await res.json();
  return data.email as string;
}

export default function LoginScreen() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword]     = useState('');
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);

  const handleLogin = async () => {
    if (!identifier.trim() || !password) {
      setError('Rellena todos los campos');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const email = await resolveIdentifier(identifier.trim().toLowerCase());
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) {
        if (authError.message.toLowerCase().includes('verif')) {
          setError('Debes verificar tu correo antes de iniciar sesión');
        } else {
          setError('Email, usuario o contraseña incorrectos');
        }
      }
    } catch (e: any) {
      setError(e.message ?? 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View className="flex-1 px-8 justify-center gap-8">
          <AuthHeader title="CanoBot" subtitle="Asistente de Domótica" />

          <View className="gap-4">
            <FormField
              label="Email o usuario"
              value={identifier}
              onChangeText={setIdentifier}
              placeholder="tu@email.com  o  mi_usuario"
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <FormField
              label="Contraseña"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
            />
            <ErrorMessage message={error} />
            <Button label="Iniciar sesión" onPress={handleLogin} loading={loading} />
          </View>

          <TouchableOpacity onPress={() => router.push('/forgot-password' as any)} className="self-center">
            <Text className="text-primary text-sm font-semibold">¿Olvidaste la contraseña?</Text>
          </TouchableOpacity>

          <View className="flex-row justify-center gap-1">
            <Text className="text-text-secondary text-sm">¿No tienes cuenta?</Text>
            <TouchableOpacity onPress={() => router.push('/register' as any)}>
              <Text className="text-primary text-sm font-semibold">Regístrate</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
