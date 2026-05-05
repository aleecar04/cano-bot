import { useState, useEffect, useCallback } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getMyCommandHistory, type CommandDto, type CommandHistoryFilters } from '@/api/devices';

// ── Labels & icons ────────────────────────────────────────────────────────────

const ACTION_LABELS: Record<string, string> = {
  encender:      'Encender',
  apagar:        'Apagar',
  brillo:        'Brillo',
  subir_volumen: 'Subir volumen',
  bajar_volumen: 'Bajar volumen',
  mute:          'Silenciar',
  set_volumen:   'Ajustar volumen',
  abrir_app:     'Abrir app',
};

const SOURCE_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  direct:       { label: 'Directo',      icon: 'phone-portrait-outline', color: '#3b82f6' },
  conversation: { label: 'Chat',         icon: 'chatbubble-outline',     color: '#8b5cf6' },
  favorite:     { label: 'Favorito',     icon: 'star-outline',           color: '#f59e0b' },
  schedule:     { label: 'Tarea',        icon: 'time-outline',           color: '#10b981' },
};

const SOURCE_FILTERS: { value: CommandDto['source_type'] | 'all'; label: string }[] = [
  { value: 'all',          label: 'Todos'     },
  { value: 'direct',       label: 'Directo'   },
  { value: 'conversation', label: 'Chat'      },
  { value: 'favorite',     label: 'Favorito'  },
  { value: 'schedule',     label: 'Tarea'     },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: CommandDto['status'] }) {
  const config = {
    executed: { color: '#22c55e', bg: '#22c55e15', label: 'OK'        },
    failed:   { color: '#ef4444', bg: '#ef444415', label: 'Error'     },
    pending:  { color: '#f59e0b', bg: '#f59e0b15', label: 'Pendiente' },
    sent:     { color: '#3b82f6', bg: '#3b82f615', label: 'Enviado'   },
  }[status] ?? { color: '#94a3b8', bg: '#94a3b815', label: status };

  return (
    <View style={{ backgroundColor: config.bg }} className="flex-row items-center gap-1 px-2 py-0.5 rounded-full">
      <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: config.color }} />
      <Text style={{ color: config.color }} className="text-xs font-semibold">{config.label}</Text>
    </View>
  );
}

function SourceBadge({ sourceType }: { sourceType: string }) {
  const cfg = SOURCE_CONFIG[sourceType] ?? { label: sourceType, icon: 'flash-outline', color: '#94a3b8' };
  return (
    <View className="flex-row items-center gap-1">
      <Ionicons name={cfg.icon as any} size={11} color={cfg.color} />
      <Text style={{ color: cfg.color }} className="text-xs">{cfg.label}</Text>
    </View>
  );
}

function CommandRow({ cmd }: { readonly cmd: CommandDto }) {
  const actionLabel = ACTION_LABELS[cmd.action] ?? cmd.action;
  const deviceName  = cmd.devices?.name ?? null;
  const dateStr     = cmd.executed_at ?? cmd.created_at;
  const date        = dateStr
    ? new Date(dateStr).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })
    : '—';
  const appPayload  = cmd.payload?.app as string | undefined;

  return (
    <View className="bg-bg-secondary border border-border rounded-xl px-4 py-3 mb-2">
      <View className="flex-row items-start justify-between gap-2">
        <View className="flex-1">
          <Text className="text-text font-semibold text-sm">
            {actionLabel}{appPayload ? ` · ${appPayload}` : ''}
          </Text>
          <View className="flex-row items-center gap-2 mt-0.5 flex-wrap">
            {deviceName && (
              <Text className="text-text-secondary text-xs">{deviceName}</Text>
            )}
            <SourceBadge sourceType={cmd.source_type} />
            <Text className="text-text-secondary text-xs">{date}</Text>
          </View>
        </View>
        <StatusBadge status={cmd.status} />
      </View>
      {!!cmd.error && (
        <Text className="text-red-400 text-xs mt-2 leading-4" numberOfLines={2}>{cmd.error}</Text>
      )}
    </View>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

export function HistoryTab() {
  const [commands, setCommands]         = useState<CommandDto[]>([]);
  const [loading, setLoading]           = useState(true);
  const [loadingMore, setLoadingMore]   = useState(false);
  const [page, setPage]                 = useState(1);
  const [hasMore, setHasMore]           = useState(true);
  const [sourceFilter, setSourceFilter] = useState<CommandDto['source_type'] | 'all'>('all');
  const [dateFrom, setDateFrom]         = useState('');
  const [dateTo, setDateTo]             = useState('');

  const buildFilters = useCallback((p: number): CommandHistoryFilters => {
    const f: CommandHistoryFilters = { limit: PAGE_SIZE, page: p };
    if (sourceFilter !== 'all') f.source_type = sourceFilter;
    if (dateFrom) f.date_from = new Date(`${dateFrom}T00:00:00`).toISOString();
    if (dateTo)   f.date_to   = new Date(`${dateTo}T23:59:59`).toISOString();
    return f;
  }, [sourceFilter, dateFrom, dateTo]);

  const load = useCallback(async () => {
    setLoading(true);
    setPage(1);
    try {
      const data = await getMyCommandHistory(buildFilters(1));
      setCommands(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [buildFilters]);

  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const data = await getMyCommandHistory(buildFilters(nextPage));
      setCommands((prev) => [...prev, ...data]);
      setPage(nextPage);
      setHasMore(data.length === PAGE_SIZE);
    } catch {
      // silent
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => { load(); }, [load]);

  return (
    <>
      {/* Header */}
      <View className="flex-row items-center justify-between mb-3">
        <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider">
          Historial de acciones
        </Text>
        <TouchableOpacity onPress={load} className="p-1.5" activeOpacity={0.7}>
          <Ionicons name="refresh" size={16} color="#94a3b8" />
        </TouchableOpacity>
      </View>

      {/* Source type filter chips */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-3">
        <View className="flex-row gap-2 pr-4">
          {SOURCE_FILTERS.map((f) => (
            <TouchableOpacity
              key={f.value}
              onPress={() => setSourceFilter(f.value)}
              className={`px-3 py-1.5 rounded-full border ${
                sourceFilter === f.value
                  ? 'bg-primary border-primary'
                  : 'bg-bg-secondary border-border'
              }`}
              activeOpacity={0.7}
            >
              <Text className={`text-xs font-semibold ${
                sourceFilter === f.value ? 'text-white' : 'text-text-secondary'
              }`}>
                {f.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </ScrollView>

      {/* Date range filter */}
      <View className="flex-row gap-2 mb-4">
        <View className="flex-1 flex-row items-center gap-2 bg-bg-secondary border border-border rounded-xl px-3 py-2">
          <Ionicons name="calendar-outline" size={14} color="#94a3b8" />
          {/* @ts-ignore */}
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            placeholder="Desde"
            style={{ background: 'transparent', border: 'none', color: '#e2e8f0', fontSize: '12px', flex: 1, outline: 'none' }}
          />
        </View>
        <View className="flex-1 flex-row items-center gap-2 bg-bg-secondary border border-border rounded-xl px-3 py-2">
          <Ionicons name="calendar-outline" size={14} color="#94a3b8" />
          {/* @ts-ignore */}
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            placeholder="Hasta"
            style={{ background: 'transparent', border: 'none', color: '#e2e8f0', fontSize: '12px', flex: 1, outline: 'none' }}
          />
        </View>
        {(dateFrom || dateTo) && (
          <TouchableOpacity
            onPress={() => { setDateFrom(''); setDateTo(''); }}
            className="w-9 h-9 bg-bg-secondary border border-border rounded-xl items-center justify-center"
            activeOpacity={0.7}
          >
            <Ionicons name="close" size={14} color="#94a3b8" />
          </TouchableOpacity>
        )}
      </View>

      {/* List */}
      {loading ? (
        <View className="py-12 items-center">
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      ) : commands.length === 0 ? (
        <View className="py-16 items-center">
          <View className="w-16 h-16 rounded-full bg-bg items-center justify-center mb-4">
            <Ionicons name="flash-outline" size={32} color="#475569" />
          </View>
          <Text className="text-text font-semibold text-base">Sin resultados</Text>
          <Text className="text-text-secondary text-sm text-center mt-2 px-6">
            No hay acciones que coincidan con los filtros aplicados
          </Text>
        </View>
      ) : (
        <>
          {commands.map((cmd) => <CommandRow key={cmd.id} cmd={cmd} />)}
          {hasMore && (
            <TouchableOpacity
              onPress={loadMore}
              disabled={loadingMore}
              className="py-3 items-center border border-border rounded-xl mt-1"
              activeOpacity={0.7}
            >
              {loadingMore
                ? <ActivityIndicator size="small" color="#94a3b8" />
                : <Text className="text-text-secondary text-sm font-semibold">Cargar más</Text>
              }
            </TouchableOpacity>
          )}
        </>
      )}
    </>
  );
}
