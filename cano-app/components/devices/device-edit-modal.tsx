import React, { useState, useEffect } from 'react';
import {
  Modal, View, Text, TextInput,
  TouchableOpacity, ScrollView, ActivityIndicator, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { updateDevice, type DeviceDto } from '@/api/devices';
import { getMyRooms, type RoomDto } from '@/api/houses';
import { friendlyError } from '@/utils/friendly-error';

interface DeviceEditModalProps {
  visible: boolean;
  device: { id: string; name: string; type?: string; room_id?: string | null };
  onClose: () => void;
  onSave: (updated: DeviceDto) => void;
  onError: (message: string) => void;
}

export function DeviceEditModal({ visible, device, onClose, onSave, onError }: Readonly<DeviceEditModalProps>) {
  const [editName, setEditName]       = useState('');
  const [editRoomId, setEditRoomId]   = useState<string | null>(null);
  const [rooms, setRooms]             = useState<RoomDto[]>([]);
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [saving, setSaving]           = useState(false);

  useEffect(() => {
    if (!visible) return;
    setEditName(device.name);
    setEditRoomId(device.room_id ?? null);
    setLoadingRooms(true);
    getMyRooms()
      .then(setRooms)
      .catch(() => setRooms([]))
      .finally(() => setLoadingRooms(false));
  }, [visible, device.name, device.room_id]);

  const handleSave = async () => {
    const name = editName.trim();
    if (!name) return;
    setSaving(true);
    try {
      const updated = await updateDevice(device.id, { name, room_id: editRoomId });
      onSave(updated);
      onClose();
    } catch (err) {
      onError(friendlyError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={() => { if (!saving) onClose(); }}
    >
      <View className="flex-1 bg-black/60 items-center justify-center px-6">
        <View className="bg-bg-secondary border border-border rounded-2xl w-full max-w-sm">

          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <Text className="text-text font-bold text-base">Editar dispositivo</Text>
            <TouchableOpacity onPress={onClose} disabled={saving} activeOpacity={0.7}>
              <Ionicons name="close" size={20} color="#94a3b8" />
            </TouchableOpacity>
          </View>

          <View className="px-5 py-4 gap-4">
            <View>
              <Text className="text-text-secondary text-xs font-semibold mb-2">Nombre</Text>
              <TextInput
                className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm"
                style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
                value={editName}
                onChangeText={setEditName}
                placeholder="Nombre del dispositivo"
                placeholderTextColor="#475569"
                editable={!saving}
                maxLength={50}
                autoFocus
              />
            </View>

            <View className="flex-row items-center gap-2 bg-bg border border-border rounded-xl px-4 py-3">
              <Ionicons name="lock-closed-outline" size={15} color="#64748b" />
              <View className="flex-1">
                <Text className="text-text text-sm font-semibold">{device.type}</Text>
                <Text className="text-text-secondary text-xs mt-0.5">Una vez vinculado, el tipo no se puede cambiar</Text>
              </View>
            </View>

            <View>
              <Text className="text-text-secondary text-xs font-semibold mb-2">Habitación</Text>
              {loadingRooms ? (
                <ActivityIndicator size="small" color="#3B82F6" />
              ) : (
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View className="flex-row gap-2 pr-2">
                    <TouchableOpacity
                      onPress={() => setEditRoomId(null)}
                      className={`px-3 py-2 rounded-lg border ${
                        editRoomId === null ? 'bg-primary border-primary' : 'bg-bg border-border'
                      }`}
                      activeOpacity={0.7}
                    >
                      <Text className={`text-xs font-semibold ${editRoomId === null ? 'text-white' : 'text-text-secondary'}`}>
                        Sin habitación
                      </Text>
                    </TouchableOpacity>
                    {rooms.map((r) => (
                      <TouchableOpacity
                        key={r.id}
                        onPress={() => setEditRoomId(r.id)}
                        className={`px-3 py-2 rounded-lg border ${
                          editRoomId === r.id ? 'bg-primary border-primary' : 'bg-bg border-border'
                        }`}
                        activeOpacity={0.7}
                      >
                        <Text className={`text-xs font-semibold ${editRoomId === r.id ? 'text-white' : 'text-text-secondary'}`}>
                          {r.name}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </ScrollView>
              )}
            </View>
          </View>

          <View className="flex-row gap-3 px-5 pb-5">
            <TouchableOpacity
              className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
              onPress={onClose}
              disabled={saving}
              activeOpacity={0.7}
            >
              <Text className="text-text font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${
                !editName.trim() || saving ? 'bg-primary/40' : 'bg-primary'
              }`}
              onPress={handleSave}
              disabled={!editName.trim() || saving}
              activeOpacity={0.8}
            >
              {saving
                ? <ActivityIndicator color="white" size="small" />
                : <Ionicons name="checkmark" size={16} color="white" />
              }
              <Text className="text-text font-semibold text-sm">Guardar</Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>
    </Modal>
  );
}
