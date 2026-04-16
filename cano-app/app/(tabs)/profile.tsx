import { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity,
  Alert, ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '@/api/supabase';
import { getUserProfile } from '@/api/api';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { ScreenHeader } from '@/components/ui/screen-header';
import { ProfileInfoCard } from '@/components/profile/profile-info-card';
import { STYLES } from '@/constants/styles';

type UserProfile = {
  id: string;
  email: string;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  xmpp_jid: string | null;
};

export default function ProfileScreen() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  useEffect(() => { loadUserProfile(); }, []);

  const loadUserProfile = async () => {
    try {
      const profile = await getUserProfile();
      setUser({
        id: profile.id,
        email: profile.email ?? '',
        username: profile.username,
        first_name: profile.first_name,
        last_name: profile.last_name,
        xmpp_jid: profile.xmpp_jid,
      });
    } catch {
      Alert.alert('Error', 'No se pudo cargar el perfil');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError('Rellena todos los campos');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Las contraseñas no coinciden');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    setChangingPassword(true);
    setPasswordError(null);
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      Alert.alert('Éxito', 'Contraseña cambiada correctamente');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setShowPasswordChange(false);
    } catch (error: any) {
      setPasswordError(error.message || 'No se pudo cambiar la contraseña');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleLogout = () => setShowLogoutConfirm(true);

  const ejecutarSignOut = async () => {
    setShowLogoutConfirm(false);
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  if (loading) {
    return (
      <View className="flex-1 bg-bg items-center justify-center">
        <ActivityIndicator size="large" color="#3B82F6" />
      </View>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView className="flex-1 px-4 py-6">
          <ScreenHeader title="Mi Perfil" subtitle="👤 Información de tu cuenta" />

          <ProfileInfoCard
            title="Información Personal"
            rows={[
              { label: 'Usuario', value: user?.username ?? '-' },
              { label: 'Nombre', value: user?.first_name ?? 'No configurado' },
              { label: 'Apellidos', value: user?.last_name ?? 'No configurado' },
              { label: 'Correo electrónico', value: user?.email ?? '-' },
            ]}
          />

          <ProfileInfoCard
            title="Cuenta XMPP"
            rows={[
              { label: 'JID', value: user?.xmpp_jid ?? 'No configurada' },
            ]}
          />

          {/* Seguridad */}
          <View className={`${STYLES.cards.light} mb-8`}>
            <TouchableOpacity
              onPress={() => setShowPasswordChange(!showPasswordChange)}
              activeOpacity={0.7}
              className="flex-row items-center justify-between"
            >
              <View className="flex-row items-center gap-2">
                <Ionicons name="lock-closed" size={18} color="#3B82F6" />
                <Text className={STYLES.headers.sectionTitle}>Seguridad</Text>
              </View>
              <Text className="text-primary text-lg">{showPasswordChange ? '−' : '+'}</Text>
            </TouchableOpacity>

            {showPasswordChange && (
              <View className="gap-4 mt-6 pt-6 border-t border-border">
                <FormField
                  label="Contraseña actual"
                  value={currentPassword}
                  onChangeText={setCurrentPassword}
                  placeholder="••••••••"
                  secureTextEntry
                  editable={!changingPassword}
                />
                <FormField
                  label="Nueva contraseña"
                  value={newPassword}
                  onChangeText={setNewPassword}
                  placeholder="••••••••"
                  secureTextEntry
                  editable={!changingPassword}
                />
                <FormField
                  label="Confirmar contraseña"
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  placeholder="••••••••"
                  secureTextEntry
                  editable={!changingPassword}
                />
                <ErrorMessage message={passwordError} />
                <Button
                  label="Cambiar Contraseña"
                  onPress={handleChangePassword}
                  loading={changingPassword}
                />
              </View>
            )}
          </View>

          <Button label="Cerrar Sesión" onPress={handleLogout} variant="danger" />
        </ScrollView>
      </KeyboardAvoidingView>

      <ConfirmModal
        visible={showLogoutConfirm}
        title="Cerrar sesión"
        message="¿Seguro que quieres salir?"
        confirmLabel="Cerrar sesión"
        cancelLabel="Cancelar"
        destructive
        onConfirm={ejecutarSignOut}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </SafeAreaView>
  );
}