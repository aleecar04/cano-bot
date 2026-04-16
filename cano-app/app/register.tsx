import { useState } from 'react';
import {
  View, Text, TouchableOpacity,
  KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { supabase } from '../api/supabase';
import { AuthHeader } from '@/components/auth/auth-header';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

// ── Validation helpers ────────────────────────────────────────────────────────

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USERNAME_RE = /^[a-z0-9_]{3,50}$/;

function validate(fields: {
  firstName: string;
  lastName: string;
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}): string | null {
  const { firstName, lastName, username, email, password, confirmPassword } = fields;

  if (!firstName.trim() || !lastName.trim() || !username || !email || !password || !confirmPassword) {
    return 'Rellena todos los campos';
  }
  if (!EMAIL_RE.test(email)) {
    return 'El email no tiene un formato válido';
  }
  if (!USERNAME_RE.test(username)) {
    return 'El usuario solo puede tener letras minúsculas, números y guiones bajos (3–50 caracteres)';
  }
  if (password.length < 8) {
    return 'La contraseña debe tener al menos 8 caracteres';
  }
  if (!/[A-Z]/.test(password)) {
    return 'La contraseña debe incluir al menos una letra mayúscula';
  }
  if (!/\d/.test(password)) {
    return 'La contraseña debe incluir al menos un número';
  }
  if (password !== confirmPassword) {
    return 'Las contraseñas no coinciden';
  }
  return null;
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function RegisterScreen() {
  const router = useRouter();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    const validationError = validate({ firstName, lastName, username, email, password, confirmPassword });
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/users/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          username,
          password,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
        }),
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
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          className="flex-1"
          contentContainerClassName="px-8 py-12 gap-8"
          keyboardShouldPersistTaps="handled"
        >
          <AuthHeader title="Crear cuenta" subtitle="Únete a CanoBot" />

          <View className="gap-4">
            {/* Name row */}
            <View className="flex-row gap-3">
              <View className="flex-1">
                <FormField
                  label="Nombre"
                  value={firstName}
                  onChangeText={setFirstName}
                  placeholder="Ana"
                  autoCapitalize="words"
                />
              </View>
              <View className="flex-1">
                <FormField
                  label="Apellidos"
                  value={lastName}
                  onChangeText={setLastName}
                  placeholder="García"
                  autoCapitalize="words"
                />
              </View>
            </View>

            <FormField
              label="Usuario"
              value={username}
              onChangeText={(v) => setUsername(v.toLowerCase().replaceAll(/[^a-z0-9_]/g, ''))}
              placeholder="mi_usuario"
            />
            <FormField
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="tu@email.com"
              keyboardType="email-address"
            />
            <FormField
              label="Contraseña"
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              secureTextEntry
            />
            <FormField
              label="Confirmar contraseña"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              placeholder="••••••••"
              secureTextEntry
            />

            {/* Password hint */}
            <Text className="text-text-secondary text-xs leading-4 -mt-1">
              Mínimo 8 caracteres, una mayúscula y un número.
            </Text>

            <ErrorMessage message={error} />
            <Button label="Crear cuenta" onPress={handleRegister} loading={loading} />
          </View>

          <View className="flex-row justify-center gap-1">
            <Text className="text-text-secondary text-sm">¿Ya tienes cuenta?</Text>
            <TouchableOpacity onPress={() => router.back()}>
              <Text className="text-primary text-sm font-semibold">Inicia sesión</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
