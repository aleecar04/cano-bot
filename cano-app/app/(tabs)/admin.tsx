import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, ActivityIndicator,
  TouchableOpacity, RefreshControl, TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useUserProfile } from '@/context/user-profile';
import {
  getAdminStats, getAdminDevices, getAdminCommands, getAdminSchedules,
  getAdminHouses, deleteAdminHouse,
  AdminStatsDto, AdminDeviceDto, AdminCommandDto, AdminScheduleDto, AdminHouseDto,
  DeviceFilters, CommandFilters, ScheduleFilters,
} from '@/api/admin';
import { ScreenHeader } from '@/components/ui/screen-header';
import { STYLES } from '@/constants/styles';

// ── Types ─────────────────────────────────────────────────────────────────────

type Section = 'devices' | 'commands' | 'schedules' | 'houses';

// ── Small reusable pieces ─────────────────────────────────────────────────────

function StatCard({ label, value, icon, color }: {
  label: string; value: number; icon: string; color: string;
}) {
  return (
    <View className="flex-1 bg-card border border-border rounded-2xl p-3 items-center gap-1">
      <Ionicons name={icon as any} size={20} color={color} />
      <Text className="text-text text-xl font-bold">{value}</Text>
      <Text className="text-text-secondary text-xs text-center leading-3">{label}</Text>
    </View>
  );
}

function SectionTab({ label, active, onPress }: {
  label: string; active: boolean; onPress: () => void;
}) {
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

function FilterChip({ label, active, onPress }: {
  label: string; active: boolean; onPress: () => void;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      className={`px-3 py-1.5 rounded-full border ${
        active ? 'bg-primary border-primary' : 'bg-transparent border-border'
      }`}
    >
      <Text className={`text-xs font-medium ${active ? 'text-white' : 'text-text-secondary'}`}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function FilterInput({ placeholder, value, onChangeText }: Readonly<{
  placeholder: string; value: string; onChangeText: (v: string) => void;
}>) {
  return (
    <TextInput
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor="#64748B"
      className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-text text-xs"
    />
  );
}

function EmptyState({ message }: { message: string }) {
  return <Text className="text-text-secondary text-sm py-4 text-center">{message}</Text>;
}

// ── Device section ────────────────────────────────────────────────────────────

function DeviceRow({ d }: { d: AdminDeviceDto }) {
  const location = [d.floor_name, d.room_name].filter(Boolean).join(' › ');
  return (
    <View className="flex-row items-start gap-3 py-3 border-b border-border">
      <View className={`w-2 h-2 rounded-full mt-1.5 ${d.is_online ? 'bg-green-500' : 'bg-slate-500'}`} />
      <View className="flex-1 min-w-0 gap-0.5">
        <Text className="text-text text-sm font-medium" numberOfLines={1}>{d.name}</Text>
        <Text className="text-text-secondary text-xs" numberOfLines={1}>
          {d.type} · {d.ip}
        </Text>
        {location ? (
          <Text className="text-text-secondary text-xs" numberOfLines={1}>
            📍 {location}
          </Text>
        ) : null}
        <Text className="text-text-secondary text-xs" numberOfLines={1}>
          👤 {d.owner?.username ?? d.owner_id}
        </Text>
      </View>
      <Text className={`text-xs font-semibold pt-0.5 ${d.is_online ? 'text-green-400' : 'text-text-secondary'}`}>
        {d.is_online ? 'Online' : 'Offline'}
      </Text>
    </View>
  );
}

function DevicesSection() {
  const [devices, setDevices] = useState<AdminDeviceDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [userFilter, setUserFilter] = useState('');
  const [onlineFilter, setOnlineFilter] = useState<boolean | undefined>(undefined);
  const [typeFilter, setTypeFilter] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (filters: DeviceFilters) => {
    setLoading(true);
    setError(null);
    try {
      setDevices(await getAdminDevices(filters));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const filters: DeviceFilters = {};
    if (userFilter.trim()) filters.user_id = userFilter.trim();
    if (onlineFilter !== undefined) filters.is_online = onlineFilter;
    if (typeFilter.trim()) filters.device_type = typeFilter.trim();

    const t = setTimeout(() => load(filters), 400);
    return () => clearTimeout(t);
  }, [userFilter, onlineFilter, typeFilter, load]);

  return (
    <View className="gap-4">
      {/* Filters */}
      <View className={`${STYLES.cards.light} gap-3`}>
        <Text className={STYLES.headers.sectionTitle}>Filtros</Text>
        <View className="flex-row gap-2">
          <FilterInput placeholder="ID de usuario" value={userFilter} onChangeText={setUserFilter} />
          <FilterInput placeholder="Tipo (tv, light…)" value={typeFilter} onChangeText={setTypeFilter} />
        </View>
        <View className="flex-row gap-2">
          <FilterChip label="Todos" active={onlineFilter === undefined} onPress={() => setOnlineFilter(undefined)} />
          <FilterChip label="Online" active={onlineFilter === true} onPress={() => setOnlineFilter(true)} />
          <FilterChip label="Offline" active={onlineFilter === false} onPress={() => setOnlineFilter(false)} />
        </View>
      </View>

      {/* Results */}
      <View className={`${STYLES.cards.light}`}>
        <Text className={STYLES.headers.sectionTitle}>Dispositivos ({devices.length})</Text>
        {loading && <ActivityIndicator size="small" color="#3B82F6" />}
        {!loading && Boolean(error) && <Text className="text-red-400 text-sm">{error}</Text>}
        {!loading && !error && devices.length === 0 && <EmptyState message="Sin resultados." />}
        {!loading && !error && devices.map((d) => <DeviceRow key={d.id} d={d} />)}
      </View>
    </View>
  );
}

// ── Commands section ──────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  executed: 'text-green-400',
  failed: 'text-red-400',
  pending: 'text-yellow-400',
  sent: 'text-blue-400',
};

const SOURCE_LABELS: Record<string, string> = {
  direct: 'Directo', conversation: 'Chat', favorite: 'Favorito', schedule: 'Tarea',
};

function CommandRow({ c }: { readonly c: AdminCommandDto }) {
  const date = c.created_at ? new Date(c.created_at).toLocaleString('es-ES') : '-';
  return (
    <View className="py-3 border-b border-border gap-0.5">
      <View className="flex-row items-center justify-between">
        <Text className="text-text text-sm font-medium">{c.action}</Text>
        <View className="flex-row items-center gap-2">
          <Text className="text-text-secondary text-xs">{SOURCE_LABELS[c.source_type] ?? c.source_type}</Text>
          <Text className={`text-xs font-semibold ${STATUS_COLORS[c.status] ?? 'text-text-secondary'}`}>
            {c.status}
          </Text>
        </View>
      </View>
      <Text className="text-text-secondary text-xs">
        👤 {c.user?.username ?? c.user_id} · 📱 {c.device?.name ?? c.device_id ?? '-'}
      </Text>
      <Text className="text-text-secondary text-xs">{date}</Text>
      {!!c.error && <Text className="text-red-400 text-xs" numberOfLines={2}>{c.error}</Text>}
    </View>
  );
}

function CommandsSection() {
  const [commands, setCommands] = useState<AdminCommandDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [userFilter, setUserFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState<string | null>(null);

  const STATUS_OPTIONS = ['', 'executed', 'failed', 'pending', 'sent'];

  const load = useCallback(async (filters: CommandFilters) => {
    setLoading(true);
    setError(null);
    try {
      setCommands(await getAdminCommands(filters));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const filters: CommandFilters = { limit: 50 };
    if (userFilter.trim()) filters.user_id = userFilter.trim();
    if (dateFrom.trim()) filters.date_from = dateFrom.trim();
    if (dateTo.trim()) filters.date_to = dateTo.trim();
    if (statusFilter) filters.status = statusFilter;

    const t = setTimeout(() => load(filters), 400);
    return () => clearTimeout(t);
  }, [userFilter, dateFrom, dateTo, statusFilter, load]);

  return (
    <View className="gap-4">
      <View className={`${STYLES.cards.light} gap-3`}>
        <Text className={STYLES.headers.sectionTitle}>Filtros</Text>
        <View className="flex-row gap-2">
          <FilterInput placeholder="ID de usuario" value={userFilter} onChangeText={setUserFilter} />
        </View>
        <View className="flex-row gap-2">
          <FilterInput placeholder="Desde (YYYY-MM-DD)" value={dateFrom} onChangeText={setDateFrom} />
          <FilterInput placeholder="Hasta (YYYY-MM-DD)" value={dateTo} onChangeText={setDateTo} />
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View className="flex-row gap-2">
            {STATUS_OPTIONS.map((s) => (
              <FilterChip
                key={s || 'all'}
                label={s || 'Todos'}
                active={statusFilter === s}
                onPress={() => setStatusFilter(s)}
              />
            ))}
          </View>
        </ScrollView>
      </View>

      <View className={`${STYLES.cards.light}`}>
        <Text className={STYLES.headers.sectionTitle}>Acciones ({commands.length})</Text>
        {loading && <ActivityIndicator size="small" color="#3B82F6" />}
        {!loading && Boolean(error) && <Text className="text-red-400 text-sm">{error}</Text>}
        {!loading && !error && commands.length === 0 && <EmptyState message="Sin resultados." />}
        {!loading && !error && commands.map((c) => <CommandRow key={c.id} c={c} />)}
      </View>
    </View>
  );
}

// ── Schedules section ─────────────────────────────────────────────────────────

function ScheduleRow({ s }: { s: AdminScheduleDto }) {
  const nextRun = s.next_run_at ? new Date(s.next_run_at).toLocaleString('es-ES') : '-';
  return (
    <View className="py-3 border-b border-border gap-0.5">
      <View className="flex-row items-center justify-between">
        <Text className="text-text text-sm font-medium" numberOfLines={1}>{s.name}</Text>
        <Text className={`text-xs font-semibold ${s.is_active ? 'text-green-400' : 'text-text-secondary'}`}>
          {s.is_active ? 'Activa' : 'Inactiva'}
        </Text>
      </View>
      <Text className="text-text-secondary text-xs">
        👤 {s.user?.username ?? s.user_id} · 📱 {s.device?.name ?? s.device_id}
      </Text>
      <Text className="text-text-secondary text-xs">
        {s.action}{s.cron_expr ? ` · ${s.cron_expr}` : ''}
      </Text>
      <Text className="text-text-secondary text-xs">Próxima ejecución: {nextRun}</Text>
      {!s.last_command_id && (
        <Text className="text-text-secondary text-xs">Sin ejecuciones registradas</Text>
      )}
    </View>
  );
}

function SchedulesSection() {
  const [schedules, setSchedules] = useState<AdminScheduleDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [userFilter, setUserFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (filters: ScheduleFilters) => {
    setLoading(true);
    setError(null);
    try {
      setSchedules(await getAdminSchedules(filters));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const filters: ScheduleFilters = {};
    if (userFilter.trim()) filters.user_id = userFilter.trim();
    if (activeFilter !== undefined) filters.is_active = activeFilter;

    const t = setTimeout(() => load(filters), 400);
    return () => clearTimeout(t);
  }, [userFilter, activeFilter, load]);

  return (
    <View className="gap-4">
      <View className={`${STYLES.cards.light} gap-3`}>
        <Text className={STYLES.headers.sectionTitle}>Filtros</Text>
        <FilterInput placeholder="ID de usuario" value={userFilter} onChangeText={setUserFilter} />
        <View className="flex-row gap-2">
          <FilterChip label="Todas" active={activeFilter === undefined} onPress={() => setActiveFilter(undefined)} />
          <FilterChip label="Activas" active={activeFilter === true} onPress={() => setActiveFilter(true)} />
          <FilterChip label="Inactivas" active={activeFilter === false} onPress={() => setActiveFilter(false)} />
        </View>
      </View>

      <View className={`${STYLES.cards.light}`}>
        <Text className={STYLES.headers.sectionTitle}>Tareas ({schedules.length})</Text>
        {loading ? (
          <ActivityIndicator size="small" color="#3B82F6" />
        ) : !!error ? (
          <Text className="text-red-400 text-sm">{error}</Text>
        ) : schedules.length === 0 ? (
          <EmptyState message="Sin resultados." />
        ) : (
          schedules.map((s) => <ScheduleRow key={s.id} s={s} />)
        )}
      </View>
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

// ── Houses section ────────────────────────────────────────────────────────────

function HousesSection() {
  const [houses, setHouses] = useState<AdminHouseDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAdminHouses();
      setHouses(data);
    } catch {
      setError('Error cargando casas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = (house: AdminHouseDto) => {
    const { Alert } = require('react-native');
    Alert.alert(
      'Eliminar casa',
      `¿Eliminar la casa "${house.name ?? house.id}"? Esta acción es irreversible.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar', style: 'destructive',
          onPress: async () => {
            setDeleting(house.id);
            try {
              await deleteAdminHouse(house.id);
              setHouses((prev) => prev.filter((h) => h.id !== house.id));
            } finally {
              setDeleting(null);
            }
          },
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
              <Text className="text-text-secondary text-xs">Bot: {h.bot_jid ?? '—'}</Text>
              <Text className="text-text-secondary text-xs">
                Propietario: {h.owner ? `${h.owner.username} (${h.owner.email})` : 'Sin propietario'}
              </Text>
              <Text className="text-text-secondary text-xs">{h.member_count} miembro{h.member_count !== 1 ? 's' : ''}</Text>
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


export default function AdminScreen() {
  const router = useRouter();
  const { profile } = useUserProfile();

  const [stats, setStats] = useState<AdminStatsDto | null>(null);
  const [section, setSection] = useState<Section>('devices');
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
          <View className="gap-2 mb-6">
            <View className="flex-row gap-2">
              <StatCard label="Usuarios" value={stats.users} icon="people" color="#3B82F6" />
              <StatCard label="Dispositivos" value={stats.devices} icon="hardware-chip" color="#8B5CF6" />
              <StatCard label="Online" value={stats.devices_online} icon="wifi" color="#10B981" />
              <StatCard label="Offline" value={stats.devices_offline} icon="wifi-outline" color="#6B7280" />
            </View>
            <View className="flex-row gap-2">
              <StatCard label="Tareas" value={stats.schedules} icon="time" color="#F59E0B" />
              <StatCard label="T. activas" value={stats.schedules_active} icon="checkmark-circle" color="#10B981" />
              <StatCard label="Acciones" value={stats.commands} icon="flash" color="#EF4444" />
            </View>
          </View>
        ) : null}

        {/* Section tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-4">
          <View className="flex-row bg-bg-secondary border border-border rounded-xl p-1 gap-1">
            <SectionTab label="Dispositivos" active={section === 'devices'} onPress={() => setSection('devices')} />
            <SectionTab label="Acciones" active={section === 'commands'} onPress={() => setSection('commands')} />
            <SectionTab label="Tareas" active={section === 'schedules'} onPress={() => setSection('schedules')} />
            <SectionTab label="Casas" active={section === 'houses'} onPress={() => setSection('houses')} />
          </View>
        </ScrollView>

        {section === 'devices' && <DevicesSection />}
        {section === 'commands' && <CommandsSection />}
        {section === 'schedules' && <SchedulesSection />}
        {section === 'houses' && <HousesSection />}

        <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
