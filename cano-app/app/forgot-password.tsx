import { useState } from 'react';
import {
  View, Text, TouchableOpacity, Alert,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { supabase } from '../api/supabase';
import { AuthHeader } from '@/components/auth/auth-header';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      setError('Introduce tu email');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const redirectTo =
        Platform.OS === 'web'
          ? `${window.location.origin}/reset-password`
          : 'cano4://reset-password';
      const { error: err } = await supabase.auth.resetPasswordForEmail(trimmed, { redirectTo });
      if (err) throw err;
      Alert.alert(
        'Email enviado',
        'Si el email existe, recibirás un enlace para restablecer tu contraseña. Revisa tu bandeja de entrada.',
        [{ text: 'OK', onPress: () => router.back() }],
      );
    } catch (e: any) {
      setError(e.message ?? 'No se pudo enviar el email');
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
          <AuthHeader title="Recuperar contraseña" subtitle="Te enviaremos un enlace por email" />

          <View className="gap-4">
            <FormField
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="tu@email.com"
              autoCapitalize="none"
              keyboardType="email-address"
            />
            <ErrorMessage message={error} />
            <Button label="Enviar enlace" onPress={handleSubmit} loading={loading} />
          </View>

          <View className="flex-row justify-center">
            <TouchableOpacity onPress={() => router.back()}>
              <Text className="text-primary text-sm font-semibold">Volver al inicio de sesión</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
