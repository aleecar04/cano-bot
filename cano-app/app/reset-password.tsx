import { useEffect, useState } from 'react';
import {
  View, Text, TouchableOpacity, Alert,
  KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { supabase } from '../api/supabase';
import { AuthHeader } from '@/components/auth/auth-header';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';

export default function ResetPasswordScreen() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [hasValidSession, setHasValidSession] = useState(false);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setHasValidSession(!!session);
      setChecking(false);
    };
    checkSession();
  }, []);

  const handleSubmit = async () => {
    if (!password || password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    if (password !== confirm) {
      setError('Las contraseñas no coinciden');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { error: err } = await supabase.auth.updateUser({ password });
      if (err) throw err;
      Alert.alert(
        'Contraseña actualizada',
        'Ya puedes iniciar sesión con tu nueva contraseña.',
        [{ text: 'OK', onPress: async () => {
          await supabase.auth.signOut();
          router.replace('/login' as any);
        }}],
      );
    } catch (e: any) {
      setError(e.message ?? 'No se pudo actualizar la contraseña');
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <ActivityIndicator size="large" color="#3B82F6" />
      </SafeAreaView>
    );
  }

  if (!hasValidSession) {
    return (
      <SafeAreaView className="flex-1 bg-bg">
        <View className="flex-1 px-8 justify-center gap-6">
          <AuthHeader title="Enlace inválido" subtitle="El enlace ha caducado o ya se utilizó" />
          <TouchableOpacity onPress={() => router.replace('/login' as any)}>
            <Text className="text-primary text-sm font-semibold text-center">Volver al inicio de sesión</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View className="flex-1 px-8 justify-center gap-8">
          <AuthHeader title="Nueva contraseña" subtitle="Elige una contraseña nueva para tu cuenta" />

          <View className="gap-4">
            <FormField
              label="Nueva contraseña"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
            />
            <FormField
              label="Repetir contraseña"
              value={confirm}
              onChangeText={setConfirm}
              placeholder="••••••••"
              secureTextEntry
            />
            <ErrorMessage message={error} />
            <Button label="Cambiar contraseña" onPress={handleSubmit} loading={loading} />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
