import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, ActivityIndicator,
  TouchableOpacity, RefreshControl, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useUserProfile } from '@/context/user-profile';
import {
  getAdminStats, getAdminHouses, deleteAdminHouse,
  getAdminUsers, deleteAdminUser,
  AdminStatsDto, AdminHouseDto, AdminUserDto,
} from '@/api/admin';
import { ScreenHeader } from '@/components/ui/screen-header';
import { STYLES } from '@/constants/styles';

// ── Types ─────────────────────────────────────────────────────────────────────

type Section = 'houses' | 'users';

// ── Small reusable pieces ─────────────────────────────────────────────────────

function StatCard({ label, value, icon, color }: Readonly<{
  label: string; value: number; icon: string; color: string;
}>) {
  return (
    <View className="flex-1 bg-card border border-border rounded-2xl p-3 items-center gap-1">
      <Ionicons name={icon as any} size={20} color={color} />
      <Text className="text-text text-xl font-bold">{value}</Text>
      <Text className="text-text-secondary text-xs text-center leading-3">{label}</Text>
    </View>
  );
}

function SectionTab({ label, active, onPress }: Readonly<{
  label: string; active: boolean; onPress: () => void;
}>) {
  return (
    <TouchableOpacity
      onPress={onPress}
      className={`flex-1 py-2 rounded-lg items-center ${active ? 'bg-primary' : 'bg-transparent'}`}
    >
      <Text className={`text-xs font-semibold ${active ? 'text-white' : 'text-text-secondary'}`}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

// ── Houses section ────────────────────────────────────────────────────────────

function HousesSection() {
  const [houses, setHouses] = useState<AdminHouseDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setHouses(await getAdminHouses());
    } catch {
      setError('Error cargando casas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const confirmDelete = async (houseId: string) => {
    setDeleting(houseId);
    try {
      await deleteAdminHouse(houseId);
      setHouses((prev) => prev.filter((h) => h.id !== houseId));
    } finally {
      setDeleting(null);
    }
  };

  const handleDelete = (house: AdminHouseDto) => {
    Alert.alert(
      'Eliminar casa',
      `¿Eliminar la casa "${house.name ?? house.id}"? Se borrarán también sus dispositivos, plantas, habitaciones e invitaciones. Esta acción es irreversible.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar', style: 'destructive',
          onPress: () => confirmDelete(house.id),
        },
      ],
    );
  };

  return (
    <View className={STYLES.cards.light}>
      <Text className={STYLES.headers.sectionTitle}>Casas ({houses.length})</Text>
      {loading ? (
        <ActivityIndicator size="small" color="#3B82F6" />
      ) : error ? (
        <Text className="text-red-400 text-sm">{error}</Text>
      ) : houses.length === 0 ? (
        <Text className="text-text-secondary text-sm">Sin casas registradas.</Text>
      ) : (
        houses.map((h) => (
          <View key={h.id} className="flex-row items-start gap-3 py-3 border-b border-border last:border-0">
            <View className="flex-1 gap-1">
              <Text className="text-text font-semibold text-sm">{h.name ?? 'Sin nombre'}</Text>
              <Text className="text-text-secondary text-xs">
                Propietario: {h.owner ? `${h.owner.username} (${h.owner.email})` : 'Sin propietario'}
              </Text>
              <Text className="text-text-secondary text-xs">
                {h.member_count} miembro{h.member_count !== 1 ? 's' : ''} · {h.device_count} dispositivo{h.device_count !== 1 ? 's' : ''}
              </Text>
            </View>
            {deleting === h.id ? (
              <ActivityIndicator size="small" color="#ef4444" />
            ) : (
              <TouchableOpacity onPress={() => handleDelete(h)} activeOpacity={0.7}>
                <Ionicons name="trash-outline" size={18} color="#ef4444" />
              </TouchableOpacity>
            )}
          </View>
        ))
      )}
    </View>
  );
}

// ── Users section ─────────────────────────────────────────────────────────────

function UsersSection() {
  const [users, setUsers] = useState<AdminUserDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await getAdminUsers());
    } catch {
      setError('Error cargando usuarios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const confirmDelete = async (userId: string) => {
    setDeleting(userId);
    try {
      await deleteAdminUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } finally {
      setDeleting(null);
    }
  };

  const handleDelete = (user: AdminUserDto) => {
    Alert.alert(
      'Eliminar usuario',
      `¿Eliminar al usuario "${user.username}"? Se borrarán también sus casas, dispositivos, tareas y conversaciones. Esta acción es irreversible.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar', style: 'destructive',
          onPress: () => confirmDelete(user.id),
        },
      ],
    );
  };

  return (
    <View className={STYLES.cards.light}>
      <Text className={STYLES.headers.sectionTitle}>Usuarios ({users.length})</Text>
      {loading ? (
        <ActivityIndicator size="small" color="#3B82F6" />
      ) : error ? (
        <Text className="text-red-400 text-sm">{error}</Text>
      ) : users.length === 0 ? (
        <Text className="text-text-secondary text-sm">Sin usuarios registrados.</Text>
      ) : (
        users.map((u) => {
          const fullName = [u.first_name, u.last_name].filter(Boolean).join(' ');
          const registered = u.created_at ? new Date(u.created_at).toLocaleDateString('es-ES') : '-';
          return (
            <View key={u.id} className="flex-row items-start gap-3 py-3 border-b border-border last:border-0">
              <View className="flex-1 gap-1">
                <View className="flex-row items-center gap-2">
                  <Text className="text-text font-semibold text-sm">{u.username}</Text>
                  {u.is_superuser && (
                    <Text className="text-yellow-400 text-xs font-semibold">admin</Text>
                  )}
                </View>
                {!!fullName && <Text className="text-text-secondary text-xs">{fullName}</Text>}
                <Text className="text-text-secondary text-xs">{u.email ?? 'sin email'}</Text>
                <Text className="text-text-secondary text-xs">Alta: {registered}</Text>
              </View>
              {deleting === u.id ? (
                <ActivityIndicator size="small" color="#ef4444" />
              ) : (
                <TouchableOpacity onPress={() => handleDelete(u)} activeOpacity={0.7}>
                  <Ionicons name="trash-outline" size={18} color="#ef4444" />
                </TouchableOpacity>
              )}
            </View>
          );
        })
      )}
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function AdminScreen() {
  const router = useRouter();
  const { profile } = useUserProfile();

  const [stats, setStats] = useState<AdminStatsDto | null>(null);
  const [section, setSection] = useState<Section>('houses');
  const [statsLoading, setStatsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (profile !== null && profile.is_superuser !== true) {
      router.replace('/(tabs)');
    }
  }, [profile, router]);

  const loadStats = useCallback(async () => {
    try {
      setStats(await getAdminStats());
    } catch {
      // stats non-critical
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadStats();
    setRefreshing(false);
  }, [loadStats]);

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <ScrollView
        className="flex-1 px-4"
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <ScreenHeader title="Panel Admin" subtitle="Vista global del sistema" />

        {/* Stats */}
        {statsLoading ? (
          <ActivityIndicator size="small" color="#3B82F6" className="mb-6" />
        ) : stats ? (
          <View className="flex-row gap-2 mb-6">
            <StatCard label="Usuarios"   value={stats.users}   icon="people"        color="#3B82F6" />
            <StatCard label="Casas"      value={stats.houses}  icon="home"          color="#8B5CF6" />
            <StatCard label="Disp."      value={stats.devices} icon="hardware-chip" color="#10B981" />
          </View>
        ) : null}

        {/* Section tabs */}
        <View className="flex-row bg-bg-secondary border border-border rounded-xl p-1 gap-1 mb-4">
          <SectionTab label="Casas"    active={section === 'houses'} onPress={() => setSection('houses')} />
          <SectionTab label="Usuarios" active={section === 'users'}  onPress={() => setSection('users')} />
        </View>

        {section === 'houses' && <HousesSection />}
        {section === 'users'  && <UsersSection />}

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
