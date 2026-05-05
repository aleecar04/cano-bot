import { useState } from 'react';
import { View, Text, Modal, TextInput, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface AddRoomModalProps {
  visible: boolean;
  floorId: string;
  floorName: string;
  onClose: () => void;
  onAddRoom: (floorId: string, roomName: string) => void;
}

export function AddRoomModal({ visible, floorId, floorName, onClose, onAddRoom }: AddRoomModalProps) {
  const [roomName, setRoomName] = useState('');
  const [adding, setAdding]     = useState(false);

  const handleAdd = async () => {
    if (!roomName.trim()) return;
    setAdding(true);
    try {
      await onAddRoom(floorId, roomName.trim());
      setRoomName('');
    } finally {
      setAdding(false);
    }
  };

  const handleClose = () => {
    setRoomName('');
    onClose();
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={handleClose}>
      <View className="flex-1 bg-black/60 items-center justify-center px-6">
        <View className="bg-bg-secondary border border-border rounded-2xl w-full max-w-sm">

          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <View>
              <Text className="text-text font-bold text-base">Añadir habitación</Text>
              <Text className="text-text-secondary text-xs mt-0.5">{floorName}</Text>
            </View>
            <TouchableOpacity onPress={handleClose} disabled={adding} activeOpacity={0.7}>
              <Ionicons name="close" size={20} color="#64748b" />
            </TouchableOpacity>
          </View>

          <View className="px-5 py-4">
            <Text className="text-text-secondary text-xs font-semibold mb-2">Nombre</Text>
            <TextInput
              className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm"
              value={roomName}
              onChangeText={setRoomName}
              placeholder="Ej. Salón, Cocina, Dormitorio..."
              placeholderTextColor="#475569"
              autoFocus
              editable={!adding}
              onSubmitEditing={handleAdd}
            />
          </View>

          <View className="flex-row gap-3 px-5 pb-5">
            <TouchableOpacity
              className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
              onPress={handleClose}
              disabled={adding}
              activeOpacity={0.7}
            >
              <Text className="text-text-secondary font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${
                !roomName.trim() || adding ? 'bg-primary/40' : 'bg-primary'
              }`}
              onPress={handleAdd}
              disabled={!roomName.trim() || adding}
              activeOpacity={0.8}
            >
              {adding
                ? <ActivityIndicator color="white" size="small" />
                : <Ionicons name="add" size={16} color="white" />
              }
              <Text className="text-text font-semibold text-sm">Añadir</Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>
    </Modal>
  );
}
