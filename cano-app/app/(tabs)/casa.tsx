import { useCallback, useState } from 'react';
import {
  View, ScrollView, Text, TouchableOpacity, ActivityIndicator,
  Modal, TextInput, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useRouter } from 'expo-router';
import {
  getMyHouse, addFloor, addRoom, deleteFloor, deleteRoom,
  getHouseMembers, getMyRole, floorAction,
  kickMember, leaveHouse,
  type HouseDto, type HouseMemberDto, type HouseMemberRole,
} from '@/api/houses';
import { supabase } from '@/api/supabase';
import { getDevices, type DeviceDto } from '@/api/devices';
import { RoomGrid, GroupScheduleModal, type ScheduleTarget } from '@/components/casa/room-grid';
import { RoomDevicesModal } from '@/components/casa/room-devices-modal';
import { AddRoomModal } from '@/components/casa/add-room-modal';
import { ConfirmModal } from '@/components/ui/confirm-modal';
import { Toast } from '@/components/ui/toast';
import { friendlyError } from '@/utils/friendly-error';

type CasaTab = 'hogar' | 'miembros';

const CASA_TABS: { id: CasaTab; label: string; icon: string }[] = [
  { id: 'hogar',    label: 'Hogar',    icon: 'home-outline' },
  { id: 'miembros', label: 'Miembros', icon: 'people-outline' },
];

export default function CasaScreen() {
  const router = useRouter();
  const [activeTab, setActiveTab]       = useState<CasaTab>('hogar');
  const [house, setHouse]               = useState<HouseDto | null>(null);
  const [devices, setDevices]           = useState<DeviceDto[]>([]);
  const [loading, setLoading]           = useState(true);
  const [selectedRoomId, setSelectedRoomId]     = useState<string | null>(null);
  const [showDevicesModal, setShowDevicesModal] = useState(false);
  const [roomScheduleTarget, setRoomScheduleTarget] = useState<ScheduleTarget | null>(null);
  const [toast, setToast]               = useState<{ message: string; variant: 'success' | 'error' } | null>(null);

  const [addRoomFloor, setAddRoomFloor] = useState<{ id: string; name: string } | null>(null);
  const [showAddRoomModal, setShowAddRoomModal] = useState(false);

  // Add floor modal
  const [showAddFloorModal, setShowAddFloorModal] = useState(false);
  const [newFloorName, setNewFloorName] = useState('');
  const [addingFloor, setAddingFloor]   = useState(false);

  // Delete confirmations
  const [deleteFloorTarget, setDeleteFloorTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleteRoomTarget, setDeleteRoomTarget]   = useState<{ floorId: string; id: string; name: string } | null>(null);

  // Group action loading states (room actions handled inside RoomDevicesModal)
  const [floorActionLoading, setFloorActionLoading] = useState<string | null>(null);

  // House members & role
  const [members, setMembers]         = useState<HouseMemberDto[]>([]);
  const [userRole, setUserRole]       = useState<HouseMemberRole | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [memberActionId, setMemberActionId] = useState<string | null>(null);
  const [kickTarget, setKickTarget]   = useState<HouseMemberDto | null>(null);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const isOwner = userRole === 'owner';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [houseData, devicesData] = await Promise.all([getMyHouse(), getDevices()]);
      setHouse(houseData);
      setDevices(devicesData);
      // Load member info in parallel (non-blocking if it fails)
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session) setCurrentUserId(session.user.id);
      });
      Promise.all([getHouseMembers(), getMyRole()]).then(([mem, role]) => {
        setMembers(mem);
        setUserRole(role);
      }).catch(() => {});
    } catch (err) {
      const msg = err instanceof Error ? err.message.toLowerCase() : '';
      if (!msg.includes('no encontr') && !msg.includes('not found')) {
        setToast({ message: friendlyError(err), variant: 'error' });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const handleRoomPress = (room: { id: string }) => {
    setSelectedRoomId(room.id);
    setShowDevicesModal(true);
  };

  const handleAddFloor = async () => {
    const name = newFloorName.trim();
    if (!name) return;
    setAddingFloor(true);
    try {
      const floor = await addFloor(name);
      setHouse((prev) => prev ? { ...prev, floors: [...prev.floors, { ...floor, rooms: [] }] } : prev);
      setNewFloorName('');
      setShowAddFloorModal(false);
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setAddingFloor(false);
    }
  };

  const handleAddRoom = async (floorId: string, roomName: string) => {
    try {
      const room = await addRoom(floorId, roomName);
      setHouse((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          floors: prev.floors.map((f) =>
            f.id === floorId ? { ...f, rooms: [...f.rooms, room] } : f
          ),
        };
      });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setShowAddRoomModal(false);
      setAddRoomFloor(null);
    }
  };

  const handleConfirmDeleteFloor = async () => {
    if (!deleteFloorTarget) return;
    const { id, name } = deleteFloorTarget;
    setDeleteFloorTarget(null);
    try {
      await deleteFloor(id);
      setHouse((prev) => prev ? { ...prev, floors: prev.floors.filter((f) => f.id !== id) } : prev);
      setToast({ message: `Planta "${name}" eliminada`, variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    }
  };

  const handleConfirmDeleteRoom = async () => {
    if (!deleteRoomTarget) return;
    const { floorId, id, name } = deleteRoomTarget;
    setDeleteRoomTarget(null);
    try {
      await deleteRoom(floorId, id);
      setHouse((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          floors: prev.floors.map((f) =>
            f.id === floorId ? { ...f, rooms: f.rooms.filter((r) => r.id !== id) } : f
          ),
        };
      });
      setToast({ message: `Habitación "${name}" eliminada`, variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    }
  };

  const handleFloorAction = async (id: string, action: 'encender' | 'apagar') => {
    setFloorActionLoading(id);
    try {
      await floorAction(id, action);
      const label = action === 'encender' ? 'encendidos' : 'apagados';
      setToast({ message: `Dispositivos de la planta ${label}`, variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setFloorActionLoading(null);
    }
  };

  const handleKickMember = async (member: HouseMemberDto) => {
    setMemberActionId(member.user_id);
    try {
      await kickMember(member.user_id);
      setMembers((prev) => prev.filter((m) => m.user_id !== member.user_id));
      setToast({ message: `${member.username ?? 'Usuario'} expulsado`, variant: 'success' });
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setMemberActionId(null);
      setKickTarget(null);
    }
  };

  const handleLeaveHouse = async () => {
    setShowLeaveConfirm(false);
    if (!currentUserId) return;
    setMemberActionId(currentUserId);
    try {
      await leaveHouse();
      setMembers([]);
      setUserRole(null);
      setHouse(null);
      router.replace('/house-setup' as any);
    } catch (err) {
      setToast({ message: friendlyError(err), variant: 'error' });
    } finally {
      setMemberActionId(null);
    }
  };

  const devicesInRoom = (roomId: string) => devices.filter((d) => d.room_id === roomId);
  const selectedRoom = house?.floors.flatMap((f) => f.rooms).find((r) => r.id === selectedRoomId);
  const online = devices.filter((d) => d.is_online).length;

  const floorsForGrid = (house?.floors ?? []).map((floor) => ({
    ...floor,
    rooms: floor.rooms.map((room, idx) => ({ id: room.id, name: room.name, order: idx })),
  }));


  if (loading) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center">
        <ActivityIndicator size="large" color="#3B82F6" />
      </SafeAreaView>
    );
  }

  if (!house) {
    return (
      <SafeAreaView className="flex-1 bg-bg items-center justify-center px-8">
        <Ionicons name="home-outline" size={64} color="#94a3b8" />
        <Text className="text-text text-lg font-semibold mt-4 text-center">Sin casa configurada</Text>
        <Text className="text-text-secondary text-sm text-center mt-2">
          Vuelve a registrarte o contacta con soporte.
        </Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-bg">
      {/* Header */}
      <View className="px-5 pt-4 pb-2">
        <Text className="text-text text-2xl font-black">{house.name ?? 'Mi Casa'}</Text>
        <Text className="text-text-secondary text-sm mt-0.5">
          {house.floors.length} {house.floors.length === 1 ? 'planta' : 'plantas'}
          {' · '}{devices.length} dispositivos · {online} en línea
        </Text>
      </View>

      {/* Tab selector — misma apariencia que my-panel */}
      <View className="mx-4 mt-3 mb-1 bg-bg-secondary rounded-xl p-1 flex-row border border-border">
        {CASA_TABS.map(({ id, label, icon }) => {
          const active = activeTab === id;
          return (
            <TouchableOpacity
              key={id}
              onPress={() => setActiveTab(id)}
              className={`flex-1 flex-row items-center justify-center gap-1.5 py-2 rounded-lg ${active ? 'bg-primary' : ''}`}
              activeOpacity={0.7}
            >
              <Ionicons name={icon as any} size={13} color={active ? 'white' : '#64748b'} />
              <Text className={`text-xs font-semibold ${active ? 'text-white' : 'text-text-secondary'}`}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <ScrollView className="flex-1 px-4 py-3" showsVerticalScrollIndicator={false}>

        {/* ── TAB: HOGAR ─────────────────────────────────────────────────────── */}
        {activeTab === 'hogar' && (
          <>
            {/* Online / offline counters */}
            <View className="flex-row gap-3 mb-5">
              <View className="flex-1 bg-bg-secondary border border-border rounded-xl p-4 items-center">
                <Text className="text-primary text-2xl font-bold">{online}</Text>
                <Text className="text-text-secondary text-xs mt-1">En línea</Text>
              </View>
              <View className="flex-1 bg-bg-secondary border border-border rounded-xl p-4 items-center">
                <Text className="text-text text-2xl font-bold">{devices.length - online}</Text>
                <Text className="text-text-secondary text-xs mt-1">Sin conexión</Text>
              </View>
            </View>

            {/* Floors / rooms */}
            {floorsForGrid.length === 0 ? (
              <View className="items-center py-12">
                <Ionicons name="layers-outline" size={48} color="#94a3b8" />
                <Text className="text-text-secondary text-sm mt-3 text-center">
                  No hay plantas. Añade una para organizar tus habitaciones.
                </Text>
              </View>
            ) : (
              floorsForGrid.map((floor) => (
                <RoomGrid
                  key={floor.id}
                  floorId={floor.id}
                  floorName={floor.name}
                  rooms={floor.rooms}
                  onRoomPress={handleRoomPress}
                  onAddRoom={isOwner ? () => { setAddRoomFloor({ id: floor.id, name: floor.name }); setShowAddRoomModal(true); } : undefined}
                  onDeleteFloor={isOwner ? (id, name) => setDeleteFloorTarget({ id, name }) : undefined}
                  onDeleteRoom={isOwner ? (floorId, id, name) => setDeleteRoomTarget({ floorId, id, name }) : undefined}
                  onFloorAction={handleFloorAction}
                  floorLoadingId={floorActionLoading}
                  onToast={(message, variant) => setToast({ message, variant })}
                />
              ))
            )}

            {isOwner && (
              <TouchableOpacity
                className="flex-row items-center justify-center gap-2 border border-dashed border-border rounded-xl py-4 mt-2 mb-6"
                onPress={() => { setNewFloorName(''); setShowAddFloorModal(true); }}
                activeOpacity={0.7}
              >
                <Ionicons name="add" size={18} color="#94a3b8" />
                <Text className="text-text-secondary text-sm">Añadir planta</Text>
              </TouchableOpacity>
            )}
          </>
        )}

        {/* ── TAB: MIEMBROS ──────────────────────────────────────────────────── */}
        {activeTab === 'miembros' && (
          <View className="pb-6">
            <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-3">
              {members.length} miembro{members.length !== 1 ? 's' : ''}
            </Text>
            {members.length === 0 ? (
              <View className="items-center py-16">
                <Ionicons name="people-outline" size={48} color="#94a3b8" />
                <Text className="text-text-secondary text-sm mt-3 text-center">
                  No hay miembros cargados.
                </Text>
              </View>
            ) : (
              members.map((member) => {
                const isMe     = member.user_id === currentUserId;
                const canKick  = isOwner && !isMe && member.role !== 'owner';
                const canLeave = isMe;
                const isActing = memberActionId === member.user_id;
                return (
                  <View
                    key={member.user_id}
                    className="flex-row items-center gap-3 bg-bg-secondary border border-border rounded-xl px-4 py-3 mb-2"
                  >
                    <View className="w-9 h-9 rounded-full bg-primary/10 items-center justify-center">
                      <Ionicons name="person" size={18} color="#3B82F6" />
                    </View>
                    <View className="flex-1">
                      <Text className="text-text font-semibold text-sm">
                        {member.username ?? 'Usuario'}{isMe ? ' (tú)' : ''}
                      </Text>
                    </View>
                    <View className={`rounded-full px-3 py-1 border ${
                      member.role === 'owner'
                        ? 'bg-amber-500/15 border-amber-500/30'
                        : 'bg-bg border-border'
                    }`}>
                      <Text className={`text-xs font-semibold ${
                        member.role === 'owner' ? 'text-amber-400' : 'text-text-secondary'
                      }`}>
                        {member.role === 'owner' ? 'Propietario' : 'Miembro'}
                      </Text>
                    </View>
                    {isActing ? (
                      <ActivityIndicator size="small" color="#94a3b8" />
                    ) : canKick ? (
                      <TouchableOpacity onPress={() => setKickTarget(member)} activeOpacity={0.7} className="ml-1">
                        <Ionicons name="person-remove-outline" size={18} color="#ef4444" />
                      </TouchableOpacity>
                    ) : canLeave ? (
                      <TouchableOpacity onPress={() => setShowLeaveConfirm(true)} activeOpacity={0.7} className="ml-1">
                        <Ionicons name="log-out-outline" size={18} color="#94a3b8" />
                      </TouchableOpacity>
                    ) : null}
                  </View>
                );
              })
            )}
          </View>
        )}

      </ScrollView>

      {/* Add floor modal */}
      <Modal visible={showAddFloorModal} transparent animationType="fade" onRequestClose={() => setShowAddFloorModal(false)}>
        <View className="flex-1 bg-black/60 items-center justify-center px-6">
          <View className="bg-bg-secondary border border-border rounded-2xl w-full max-w-sm p-5">
            <Text className="text-text text-base font-bold mb-4">Añadir planta</Text>
            <TextInput
              className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm mb-4"
              style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
              value={newFloorName}
              onChangeText={setNewFloorName}
              placeholder="Ej. Planta Baja, Primera planta..."
              placeholderTextColor="#64748b"
              maxLength={50}
              autoFocus
              onSubmitEditing={handleAddFloor}
            />
            <View className="flex-row gap-3">
              <TouchableOpacity
                className="flex-1 bg-red-500 rounded-xl py-3 items-center"
                onPress={() => setShowAddFloorModal(false)}
                disabled={addingFloor}
                activeOpacity={0.7}
              >
                <Text className="text-white font-semibold text-sm">Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                className={`flex-1 rounded-xl py-3 items-center ${!newFloorName.trim() || addingFloor ? 'bg-primary/40' : 'bg-primary'}`}
                onPress={handleAddFloor}
                disabled={!newFloorName.trim() || addingFloor}
                activeOpacity={0.8}
              >
                {addingFloor ? (
                  <ActivityIndicator color="white" size="small" />
                ) : (
                  <Text className="text-white font-semibold text-sm">Añadir</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <RoomDevicesModal
        visible={showDevicesModal}
        roomId={selectedRoomId ?? ''}
        roomName={selectedRoom?.name ?? ''}
        devices={devicesInRoom(selectedRoomId ?? '').map((d) => ({
          id: d.id,
          name: d.name,
          type: d.type,
          ip: d.ip,
          is_online: d.is_online,
          estado: d.estado ?? {},
          room_id: d.room_id,
        }))}
        onClose={() => setShowDevicesModal(false)}
        onCommandSuccess={load}
        onDeviceUpdate={(updated) => {
          setDevices((prev) => prev.map((d) => d.id === updated.id ? { ...d, ...updated } : d));
        }}
        onEditSuccess={(updated) => {
          setDevices((prev) => prev.map((d) => d.id === updated.id ? { ...d, ...updated } : d));
        }}
        onUnlinkDevice={(id, name) => {
          setDevices((prev) => prev.filter((d) => d.id !== id));
          setToast({ message: `${name} desvinculado`, variant: 'success' });
        }}
        onScheduleRoom={(id, name) => {
          setShowDevicesModal(false);
          setRoomScheduleTarget({ kind: 'room', id, name });
        }}
      />

      {addRoomFloor && (
        <AddRoomModal
          visible={showAddRoomModal}
          floorId={addRoomFloor.id}
          floorName={addRoomFloor.name}
          onClose={() => { setShowAddRoomModal(false); setAddRoomFloor(null); }}
          onAddRoom={handleAddRoom}
        />
      )}

      <ConfirmModal
        visible={deleteFloorTarget !== null}
        title="Eliminar planta"
        message={`¿Eliminar "${deleteFloorTarget?.name}" y todas sus habitaciones?`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={handleConfirmDeleteFloor}
        onCancel={() => setDeleteFloorTarget(null)}
      />

      <ConfirmModal
        visible={deleteRoomTarget !== null}
        title="Eliminar habitación"
        message={`¿Eliminar "${deleteRoomTarget?.name}"?`}
        confirmLabel="Eliminar"
        destructive
        onConfirm={handleConfirmDeleteRoom}
        onCancel={() => setDeleteRoomTarget(null)}
      />

      <GroupScheduleModal
        visible={roomScheduleTarget !== null}
        target={roomScheduleTarget}
        onClose={() => setRoomScheduleTarget(null)}
        onToast={(message, variant) => setToast({ message, variant })}
      />

      <ConfirmModal
        visible={kickTarget !== null}
        title="Expulsar miembro"
        message={`¿Expulsar a ${kickTarget?.username ?? 'este usuario'} de la casa?`}
        confirmLabel="Expulsar"
        onConfirm={() => kickTarget && handleKickMember(kickTarget)}
        onCancel={() => setKickTarget(null)}
      />

      <ConfirmModal
        visible={showLeaveConfirm}
        title="Salir de la casa"
        message={
          isOwner && members.length > 1
            ? 'Eres el propietario. Al salir, el rol se asignará automáticamente a otro miembro.'
            : isOwner && members.length === 1
            ? 'Eres el único miembro. Al salir, la casa y todos sus dispositivos se borrarán definitivamente.'
            : '¿Seguro que quieres salir de esta casa? Necesitarás un nuevo código para volver a unirte.'
        }
        confirmLabel="Salir"
        onConfirm={handleLeaveHouse}
        onCancel={() => setShowLeaveConfirm(false)}
      />

      <Toast
        message={toast?.message ?? ''}
        variant={toast?.variant ?? 'error'}
        visible={toast !== null}
        onHide={() => setToast(null)}
      />
    </SafeAreaView>
  );
}
