import { useRef, useState } from 'react';
import {
  View, Text, TouchableOpacity, TextInput,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { supabase } from '../api/supabase';
import { AuthHeader } from '@/components/auth/auth-header';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';
import { ONBOARDING_DONE_KEY } from './onboarding';

const API_URL = process.env.EXPO_PUBLIC_API_URL!;

const EMAIL_RE    = /^[^\s@]{1,64}@[^\s@]{1,253}\.[^\s@]{2,}$/;
const USERNAME_RE = /^[a-z0-9_]{3,50}$/;

function validate(fields: {
  firstName: string; lastName: string; username: string;
  email: string; password: string; confirmPassword: string;
}): string | null {
  const { firstName, lastName, username, email, password, confirmPassword } = fields;
  if (!firstName.trim() || !lastName.trim() || !username || !email || !password || !confirmPassword)
    return 'Rellena todos los campos';
  if (!EMAIL_RE.test(email))
    return 'El email no tiene un formato válido';
  if (!USERNAME_RE.test(username))
    return 'El usuario solo puede tener letras minúsculas, números y guiones bajos (3–50 caracteres)';
  if (password.length < 8)
    return 'La contraseña debe tener al menos 8 caracteres';
  if (!/[A-Z]/.test(password))
    return 'La contraseña debe incluir al menos una letra mayúscula';
  if (!/\d/.test(password))
    return 'La contraseña debe incluir al menos un número';
  if (password !== confirmPassword)
    return 'Las contraseñas no coinciden';
  return null;
}

type Step = 'form' | 'code';

export default function RegisterScreen() {
  const router = useRouter();

  // Form fields
  const [firstName, setFirstName]             = useState('');
  const [lastName, setLastName]               = useState('');
  const [username, setUsername]               = useState('');
  const [email, setEmail]                     = useState('');
  const [password, setPassword]               = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Flow state
  const [step, setStep]       = useState<Step>('form');
  const [code, setCode]       = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const codeInputRef = useRef<TextInput>(null);

  // ── Step 1: send verification code ───────────────────────────────────────────

  const handleSendCode = async () => {
    const validationError = validate({ firstName, lastName, username, email, password, confirmPassword });
    if (validationError) { setError(validationError); return; }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/send-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, first_name: firstName.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Error al enviar el código');
      }
      setStep('code');
      setTimeout(() => codeInputRef.current?.focus(), 300);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2: verify code and create account ────────────────────────────────────

  const handleVerifyAndCreate = async () => {
    if (code.length !== 6) { setError('Introduce el código de 6 dígitos'); return; }

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
          last_name:  lastName.trim(),
          verification_code: code,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? 'Error al crear la cuenta');
      }

      const { error: loginError } = await supabase.auth.signInWithPassword({ email, password });
      if (loginError) throw new Error(loginError.message);

      await AsyncStorage.removeItem(ONBOARDING_DONE_KEY);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView
          className="flex-1"
          contentContainerClassName="px-8 py-12 gap-8"
          keyboardShouldPersistTaps="handled"
        >
          <AuthHeader
            title={step === 'form' ? 'Crear cuenta' : 'Verifica tu email'}
            subtitle={step === 'form' ? 'Únete a CanoBot' : `Hemos enviado un código a ${email}`}
          />

          {/* ── STEP 1: form ── */}
          {step === 'form' && (
            <View className="gap-4">
              <View className="flex-row gap-3">
                <View className="flex-1">
                  <FormField label="Nombre" value={firstName} onChangeText={setFirstName}
                    placeholder="Ana" autoCapitalize="words" />
                </View>
                <View className="flex-1">
                  <FormField label="Apellidos" value={lastName} onChangeText={setLastName}
                    placeholder="García" autoCapitalize="words" />
                </View>
              </View>

              <FormField label="Usuario" value={username}
                onChangeText={(v) => setUsername(v.toLowerCase().replaceAll(/[^a-z0-9_]/g, ''))}
                placeholder="mi_usuario" autoCapitalize="none" />

              <FormField label="Email" value={email} onChangeText={setEmail}
                placeholder="tu@email.com" keyboardType="email-address" autoCapitalize="none" />

              <FormField label="Contraseña" value={password} onChangeText={setPassword}
                placeholder="••••••••" secureTextEntry />

              <FormField label="Confirmar contraseña" value={confirmPassword}
                onChangeText={setConfirmPassword} placeholder="••••••••" secureTextEntry />

              <Text className="text-text-secondary text-xs leading-4 -mt-1">
                Mínimo 8 caracteres, una mayúscula y un número.
              </Text>

              <ErrorMessage message={error} />
              <Button label="Enviar código de verificación" onPress={handleSendCode} loading={loading} />
            </View>
          )}

          {/* ── STEP 2: code ── */}
          {step === 'code' && (
            <View className="gap-5">
              <View className="bg-indigo-500/10 border border-indigo-500/30 rounded-2xl p-4 flex-row items-start gap-3">
                <Ionicons name="mail-outline" size={18} color="#818cf8" style={{ marginTop: 1 }} />
                <Text className="text-text-secondary text-sm leading-5 flex-1">
                  Revisa tu bandeja de entrada y escribe el código de 6 dígitos que te hemos enviado.
                  Válido durante <Text className="text-text font-semibold">15 minutos</Text>.
                </Text>
              </View>

              {/* Code input */}
              <View>
                <Text className="text-text-secondary text-xs font-semibold mb-2">Código de verificación</Text>
                <TextInput
                  ref={codeInputRef}
                  className="bg-bg border border-border rounded-xl px-4 py-4 text-text text-2xl font-bold tracking-widest text-center"
                  value={code}
                  onChangeText={(v) => { setCode(v.replace(/[^0-9]/g, '').slice(0, 6)); setError(null); }}
                  placeholder="000000"
                  placeholderTextColor="#475569"
                  keyboardType="number-pad"
                  maxLength={6}
                />
              </View>

              <ErrorMessage message={error} />

              <Button
                label="Verificar y crear cuenta"
                onPress={handleVerifyAndCreate}
                loading={loading}
              />

              {/* Resend */}
              <TouchableOpacity
                className="items-center py-2"
                onPress={() => { setError(null); handleSendCode(); }}
                disabled={loading}
                activeOpacity={0.7}
              >
                {loading
                  ? <ActivityIndicator size="small" color="#6366f1" />
                  : <Text className="text-primary text-sm">¿No has recibido el código? Reenviar</Text>
                }
              </TouchableOpacity>

              <TouchableOpacity
                className="items-center py-1"
                onPress={() => { setStep('form'); setCode(''); setError(null); }}
                disabled={loading}
                activeOpacity={0.7}
              >
                <Text className="text-text-secondary text-sm">← Cambiar datos</Text>
              </TouchableOpacity>
            </View>
          )}

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
