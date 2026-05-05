import { useEffect, useRef, useState } from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getDevices, type DeviceDto } from '@/api/devices';
import { getSchedules, type ScheduleDto } from '@/api/schedules';
import { getHouseMembers, getMyRole, type HouseMemberDto, type HouseMemberRole } from '@/api/houses';
import { supabase } from '@/api/supabase';
import { Toast } from '@/components/ui/toast';
import { DevicesTab } from '@/components/devices/devices-tab';
import { SchedulesTab } from '@/components/schedules/schedules-tab';
import { HistoryTab } from '@/components/history-tab';

type Tab = 'devices' | 'actions' | 'history';

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'devices', label: 'Dispositivos', icon: 'hardware-chip-outline' },
  { id: 'actions', label: 'Tareas',        icon: 'time-outline' },
  { id: 'history', label: 'Historial',     icon: 'list-outline' },
];

export default function MyPanelScreen() {
  const [activeTab, setActiveTab]   = useState<Tab>('devices');
  const [linkedDevices, setLinkedDevices] = useState<DeviceDto[]>([]);
  const [loadingDevices, setLoadingDevices] = useState(true);
  const [schedules, setSchedules]   = useState<ScheduleDto[]>([]);
  const [loadingSchedules, setLoadingSchedules] = useState(false);
  const [toast, setToast]           = useState<{ message: string; variant: 'success' | 'error' } | null>(null);

  const [currentUserId, setCurrentUserId]   = useState<string | undefined>(undefined);
  const [currentUserRole, setCurrentUserRole] = useState<HouseMemberRole | null>(null);
  const [houseMembers, setHouseMembers]     = useState<HouseMemberDto[]>([]);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadLinkedDevices();
    loadSchedules();
    loadHouseInfo();

    pollRef.current = setInterval(async () => {
      try {
        const fresh = await getDevices();
        setLinkedDevices(fresh);
      } catch {
        // silent — keep stale data
      }
    }, 30_000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const loadHouseInfo = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user.id) setCurrentUserId(session.user.id);
      const [members, role] = await Promise.all([getHouseMembers(), getMyRole()]);
      setHouseMembers(members);
      setCurrentUserRole(role);
    } catch {
      // house info is optional; silently ignore
    }
  };

  const loadLinkedDevices = async () => {
    setLoadingDevices(true);
    try {
      setLinkedDevices(await getDevices());
    } catch {
      // silent
    } finally {
      setLoadingDevices(false);
    }
  };

  const loadSchedules = async () => {
    setLoadingSchedules(true);
    try {
      setSchedules(await getSchedules());
    } catch {
      // silent
    } finally {
      setLoadingSchedules(false);
    }
  };

  const showToast = (message: string, variant: 'success' | 'error') =>
    setToast({ message, variant });

  return (
    <SafeAreaView className="flex-1 bg-bg">

      {/* Header */}
      <View className="px-5 pt-4 pb-2">
        <Text className="text-text text-2xl font-black">Mi panel</Text>
        <Text className="text-text-secondary text-sm mt-0.5">Gestiona tus dispositivos y automatizaciones</Text>
      </View>

      {/* Tab selector — segmented control style */}
      <View className="mx-4 mt-3 mb-1 bg-bg-secondary rounded-xl p-1 flex-row border border-border">
        {TABS.map(({ id, label, icon }) => {
          const active = activeTab === id;
          return (
            <TouchableOpacity
              key={id}
              onPress={() => setActiveTab(id)}
              className={`flex-1 flex-row items-center justify-center gap-1.5 py-2 rounded-lg ${
                active ? 'bg-primary' : ''
              }`}
              activeOpacity={0.7}
            >
              <Ionicons
                name={icon as any}
                size={13}
                color={active ? 'white' : '#64748b'}
              />
              <Text className={`text-xs font-semibold ${active ? 'text-white' : 'text-text-secondary'}`}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <ScrollView className="flex-1 px-4 pt-4 pb-6" showsVerticalScrollIndicator={false}>
        {activeTab === 'devices' && (
          <DevicesTab
            linkedDevices={linkedDevices}
            loadingDevices={loadingDevices}
            onLinkSuccess={(device) => setLinkedDevices((prev) => [...prev, device])}
            onUnlinkSuccess={(id) => setLinkedDevices((prev) => prev.filter((d) => d.id !== id))}
            onEditSuccess={(updated) => setLinkedDevices((prev) => prev.map((d) => d.id === updated.id ? updated : d))}
            onDeviceUpdate={(updated) => setLinkedDevices((prev) => prev.map((d) => d.id === updated.id ? updated : d))}
            onToast={showToast}
          />
        )}
        {activeTab === 'actions' && (
          <SchedulesTab
            schedules={schedules}
            loadingSchedules={loadingSchedules}
            devices={linkedDevices}
            currentUserId={currentUserId}
            currentUserRole={currentUserRole}
            houseMembers={houseMembers}
            onSchedulesChange={setSchedules}
            onToast={showToast}
          />
        )}
        {activeTab === 'history' && (
          <HistoryTab />
        )}
        <View className="h-6" />
      </ScrollView>

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'success'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </SafeAreaView>
  );
}
