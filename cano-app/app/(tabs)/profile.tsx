import { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, Modal, Clipboard,
  ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { supabase } from '@/api/supabase';
import { getUserProfile } from '@/api/api';
import { getHaConnection, connectHa, disconnectHa, type HaConnectionDto } from '@/api/ha';
import { generateInviteCode, getMyRole, type HouseMemberRole, type InviteCodeDto } from '@/api/houses';
import { FormField } from '@/components/ui/form-field';
import { ErrorMessage } from '@/components/ui/error-message';
import { Button } from '@/components/ui/button';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { Toast } from '@/components/ui/toast';

type UserProfile = {
  id: string;
  email: string;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  xmpp_jid: string | null;
};

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View className="py-3 border-b border-border/50 last:border-0">
      <Text className="text-text-secondary text-xs mb-0.5">{label}</Text>
      <Text className="text-text font-semibold text-sm">{value}</Text>
    </View>
  );
}

function SectionCard({
  icon, title, badge, expanded, onToggle, children,
}: {
  icon: string;
  title: string;
  badge?: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <View className="bg-bg-secondary border border-border rounded-2xl mb-4 overflow-hidden">
      <TouchableOpacity
        onPress={onToggle}
        activeOpacity={0.7}
        className="flex-row items-center justify-between px-4 py-4"
      >
        <View className="flex-row items-center gap-3">
          <View className="w-8 h-8 rounded-xl bg-primary/10 items-center justify-center">
            <Ionicons name={icon as any} size={16} color="#3B82F6" />
          </View>
          <Text className="text-text font-semibold text-sm">{title}</Text>
          {badge && (
            <View className="bg-green-500/15 rounded-full px-2 py-0.5">
              <Text className="text-green-400 text-xs font-semibold">{badge}</Text>
            </View>
          )}
        </View>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={16}
          color="#64748b"
        />
      </TouchableOpacity>
      {expanded && (
        <View className="px-4 pb-4 border-t border-border">
          {children}
        </View>
      )}
    </View>
  );
}

export default function ProfileScreen() {
  const router = useRouter();
  const [loading, setLoading]           = useState(true);
  const [user, setUser]                 = useState<UserProfile | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword]   = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [toast, setToast]               = useState<{ message: string; variant: 'success' | 'error' } | null>(null);

  const [showHa, setShowHa]             = useState(false);
  const [haConnection, setHaConnection] = useState<HaConnectionDto | null>(null);
  const [haUrl, setHaUrl]               = useState('');
  const [haToken, setHaToken]           = useState('');
  const [haConnecting, setHaConnecting] = useState(false);
  const [haError, setHaError]           = useState<string | null>(null);
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);

  // Invite code / house role
  const [userRole, setUserRole]           = useState<HouseMemberRole | null>(null);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteData, setInviteData]       = useState<InviteCodeDto | null>(null);
  const [generatingCode, setGeneratingCode] = useState(false);
  const [inviteError, setInviteError]     = useState<string | null>(null);

  useEffect(() => { loadUserProfile(); loadHaConnection(); loadRole(); }, []);

  const loadUserProfile = async () => {
    try {
      const profile = await getUserProfile();
      setUser({
        id:         profile.id,
        email:      profile.email ?? '',
        username:   profile.username,
        first_name: profile.first_name,
        last_name:  profile.last_name,
        xmpp_jid:   profile.xmpp_jid,
      });
    } catch {
      setToast({ message: 'No se pudo cargar el perfil', variant: 'error' });
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
      setPasswordError('Mínimo 8 caracteres');
      return;
    }
    setChangingPassword(true);
    setPasswordError(null);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const email = sessionData.session?.user.email;
      if (!email) throw new Error('No se pudo obtener la sesión');
      const { error: verifyError } = await supabase.auth.signInWithPassword({ email, password: currentPassword });
      if (verifyError) throw new Error('La contraseña actual no es correcta');
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      setToast({ message: 'Contraseña cambiada correctamente', variant: 'success' });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'No se pudo cambiar la contraseña';
      setPasswordError(msg);
    } finally {
      setChangingPassword(false);
    }
  };

  const loadHaConnection = async () => {
    try {
      const conn = await getHaConnection();
      setHaConnection(conn);
    } catch {
      // HA is optional
    }
  };

  const loadRole = async () => {
    try {
      const role = await getMyRole();
      setUserRole(role);
    } catch {
      // role is optional
    }
  };

  const handleOpenInvite = async () => {
    setInviteData(null);
    setInviteError(null);
    setShowInviteModal(true);
    setGeneratingCode(true);
    try {
      const data = await generateInviteCode();
      setInviteData(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error generando código';
      setInviteError(msg);
    } finally {
      setGeneratingCode(false);
    }
  };

  const handleCopyCode = () => {
    if (!inviteData) return;
    Clipboard.setString(inviteData.code);
    setToast({ message: 'Código copiado al portapapeles', variant: 'success' });
  };

  const handleHaConnect = async () => {
    if (!haUrl.trim() || !haToken.trim()) {
      setHaError('Introduce la URL y el token');
      return;
    }
    setHaConnecting(true);
    setHaError(null);
    try {
      const result = await connectHa(haUrl.trim(), haToken.trim());
      setHaConnection({ connected: true, ha_url: haUrl.trim() });
      setHaUrl('');
      setHaToken('');
      setToast({ message: `${result.importados} dispositivos importados de Home Assistant`, variant: 'success' });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'No se pudo conectar con Home Assistant';
      setHaError(msg);
    } finally {
      setHaConnecting(false);
    }
  };

  const handleHaDisconnect = async () => {
    setShowDisconnectConfirm(false);
    try {
      await disconnectHa();
      setHaConnection({ connected: false });
      setToast({ message: 'Home Assistant desconectado', variant: 'success' });
    } catch {
      setToast({ message: 'No se pudo desconectar Home Assistant', variant: 'error' });
    }
  };

  const ejecutarSignOut = async () => {
    setShowLogoutConfirm(false);
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'No se pudo cerrar sesión';
      setToast({ message: msg, variant: 'error' });
    }
  };

  if (loading) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <ActivityIndicator size="large" color="#3B82F6" />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>

          {/* Header */}
          <View className="px-5 pt-5 pb-4">
            <Text className="text-text-secondary text-sm font-medium">Cuenta</Text>
            <Text className="text-text text-2xl font-black mt-0.5">Mi perfil</Text>
          </View>

          <View className="px-5">

            {/* Info personal */}
            <View className="bg-bg-secondary border border-border rounded-2xl px-4 pt-3 pb-1 mb-4">
              <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">
                Información personal
              </Text>
              <InfoRow label="Usuario"            value={user?.username ?? '-'} />
              <InfoRow label="Nombre"             value={user?.first_name ?? 'No configurado'} />
              <InfoRow label="Apellidos"          value={user?.last_name ?? 'No configurado'} />
              <InfoRow label="Correo electrónico" value={user?.email ?? '-'} />
            </View>

            {/* Cuenta XMPP */}
            <View className="bg-bg-secondary border border-border rounded-2xl px-4 pt-3 pb-1 mb-4">
              <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">
                Cuenta XMPP
              </Text>
              <InfoRow label="JID" value={user?.xmpp_jid ?? 'No configurada'} />
            </View>

            {/* Seguridad */}
            <SectionCard
              icon="lock-closed-outline"
              title="Seguridad"
              expanded={showPassword}
              onToggle={() => setShowPassword(!showPassword)}
            >
              <View className="gap-4 pt-4">
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
                <Button label="Cambiar contraseña" onPress={handleChangePassword} loading={changingPassword} />
              </View>
            </SectionCard>

            {/* Home Assistant */}
            <SectionCard
              icon="home-outline"
              title="Home Assistant"
              badge={haConnection?.connected ? 'Conectado' : undefined}
              expanded={showHa}
              onToggle={() => setShowHa(!showHa)}
            >
              <View className="pt-4">
                {haConnection?.connected ? (
                  <View className="gap-3">
                    <View className="bg-bg border border-border rounded-xl px-4 py-3">
                      <Text className="text-text-secondary text-xs mb-1">Servidor</Text>
                      <Text className="text-text text-sm font-semibold">{haConnection.ha_url}</Text>
                    </View>
                    <Text className="text-text-secondary text-xs text-center">
                      Los dispositivos importados aparecen en tu panel.
                    </Text>
                    <View className="flex-row gap-3">
                      <TouchableOpacity
                        className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
                        onPress={handleHaConnect}
                        disabled={haConnecting}
                        activeOpacity={0.7}
                      >
                        <Text className="text-text-secondary font-semibold text-sm">Reimportar</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        className="flex-1 bg-red-500/10 border border-red-500/30 rounded-xl py-3 items-center"
                        onPress={() => setShowDisconnectConfirm(true)}
                        activeOpacity={0.7}
                      >
                        <Text className="text-red-400 font-semibold text-sm">Desconectar</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : (
                  <View className="gap-4">
                    <Text className="text-text-secondary text-sm leading-5">
                      Conecta tu servidor de Home Assistant para importar automáticamente todos tus dispositivos compatibles.
                    </Text>
                    <FormField
                      label="URL del servidor"
                      value={haUrl}
                      onChangeText={setHaUrl}
                      placeholder="http://192.168.1.50:8123"
                      editable={!haConnecting}
                    />
                    <FormField
                      label="Token de acceso"
                      value={haToken}
                      onChangeText={setHaToken}
                      placeholder="Long-lived access token"
                      secureTextEntry
                      editable={!haConnecting}
                    />
                    <ErrorMessage message={haError} />
                    <Button label="Conectar Home Assistant" onPress={handleHaConnect} loading={haConnecting} />
                  </View>
                )}
              </View>
            </SectionCard>

            {/* Invitar a alguien — owner only */}
            {userRole === 'owner' && (
              <TouchableOpacity
                className="flex-row items-center justify-center gap-2 bg-primary/10 border border-primary/30 rounded-2xl py-4 mb-4"
                onPress={handleOpenInvite}
                activeOpacity={0.7}
              >
                <Ionicons name="person-add-outline" size={18} color="#3B82F6" />
                <Text className="text-primary font-semibold text-sm">Invitar a alguien</Text>
              </TouchableOpacity>
            )}

            {/* Configurar casa — solo visible si el usuario no pertenece a ninguna casa */}
            {userRole === null && (
              <TouchableOpacity
                className="flex-row items-center justify-center gap-2 bg-bg-secondary border border-border rounded-2xl py-4 mb-3"
                onPress={() => router.push('/house-setup' as any)}
                activeOpacity={0.7}
              >
                <Ionicons name="home-outline" size={18} color="#3B82F6" />
                <Text className="text-text font-semibold text-sm">Configurar casa</Text>
              </TouchableOpacity>
            )}

            {/* Cerrar sesión */}
            <TouchableOpacity
              className="flex-row items-center justify-center gap-2 bg-red-500/10 border border-red-500/20 rounded-2xl py-4 mb-10"
              onPress={() => setShowLogoutConfirm(true)}
              activeOpacity={0.7}
            >
              <Ionicons name="log-out-outline" size={18} color="#ef4444" />
              <Text className="text-red-400 font-semibold text-sm">Cerrar sesión</Text>
            </TouchableOpacity>

          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Invite code modal */}
      <Modal
        visible={showInviteModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowInviteModal(false)}
      >
        <View className="flex-1 bg-black/60 items-center justify-center px-6">
          <View className="bg-bg-secondary border border-border rounded-2xl w-full max-w-sm p-6">
            {/* Header */}
            <View className="flex-row items-center justify-between mb-5">
              <Text className="text-text font-bold text-base">Invitar a alguien</Text>
              <TouchableOpacity onPress={() => setShowInviteModal(false)} hitSlop={8}>
                <Ionicons name="close" size={20} color="#64748b" />
              </TouchableOpacity>
            </View>

            {generatingCode ? (
              <View className="items-center py-8">
                <ActivityIndicator size="large" color="#3B82F6" />
                <Text className="text-text-secondary text-sm mt-3">Generando código…</Text>
              </View>
            ) : inviteError ? (
              <View className="items-center py-4">
                <Ionicons name="alert-circle-outline" size={40} color="#ef4444" />
                <Text className="text-red-400 text-sm mt-2 text-center">{inviteError}</Text>
                <TouchableOpacity
                  className="mt-4 bg-primary rounded-xl px-6 py-3"
                  onPress={handleOpenInvite}
                  activeOpacity={0.8}
                >
                  <Text className="text-text font-semibold text-sm">Reintentar</Text>
                </TouchableOpacity>
              </View>
            ) : inviteData ? (
              <View className="items-center gap-4">
                {/* Hint */}
                <Text className="text-text-secondary text-sm text-center leading-5">
                  Comparte este código con quien quieras añadir a tu hogar.
                </Text>

                {/* Code display */}
                <View className="bg-bg border border-border rounded-2xl px-8 py-5 w-full items-center">
                  <Text className="text-text text-4xl font-black tracking-widest">
                    {inviteData.code}
                  </Text>
                </View>

                {/* Expiry */}
                <View className="flex-row items-center gap-1.5">
                  <Ionicons name="time-outline" size={14} color="#94a3b8" />
                  <Text className="text-text-secondary text-xs">
                    Caduca en {inviteData.expires_in_hours} horas
                  </Text>
                </View>

                {/* Copy button */}
                <TouchableOpacity
                  className="flex-row items-center gap-2 bg-primary rounded-xl px-6 py-3 w-full justify-center"
                  onPress={handleCopyCode}
                  activeOpacity={0.8}
                >
                  <Ionicons name="copy-outline" size={16} color="white" />
                  <Text className="text-text font-semibold text-sm">Copiar código</Text>
                </TouchableOpacity>

                {/* Regenerate */}
                <TouchableOpacity onPress={handleOpenInvite} activeOpacity={0.7}>
                  <Text className="text-text-secondary text-xs underline">Generar nuevo código</Text>
                </TouchableOpacity>
              </View>
            ) : null}
          </View>
        </View>
      </Modal>

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

      <ConfirmModal
        visible={showDisconnectConfirm}
        title="Desconectar Home Assistant"
        message="Se eliminarán todos los dispositivos importados desde Home Assistant. ¿Continuar?"
        confirmLabel="Desconectar"
        cancelLabel="Cancelar"
        destructive
        onConfirm={handleHaDisconnect}
        onCancel={() => setShowDisconnectConfirm(false)}
      />

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'success'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </SafeAreaView>
  );
}
