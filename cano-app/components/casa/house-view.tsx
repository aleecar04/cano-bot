import React, { useState } from 'react';
import { View, TouchableOpacity, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { RoomGrid } from './room-grid';

interface Room {
  id: string;
  name: string;
  order: number;
}

interface Floor {
  id: string;
  name: string;
  rooms: Room[];
}

interface HouseViewProps {
  floors: Floor[];
  onRoomPress?: (room: Room) => void;
  onAddRoom?: () => void;
}

export const HouseView: React.FC<HouseViewProps> = ({
  floors,
  onRoomPress,
  onAddRoom,
}) => {
  const [expandedFloors, setExpandedFloors] = useState<Set<string>>(
    new Set(floors.slice(0, 3).map(f => f.id)) // Expandir primeras 3
  );

  const toggleFloor = (floorId: string) => {
    const newExpanded = new Set(expandedFloors);
    if (newExpanded.has(floorId)) {
      newExpanded.delete(floorId);
    } else {
      newExpanded.add(floorId);
    }
    setExpandedFloors(newExpanded);
  };

  return (
    <View className="bg-gradient-to-b from-blue-100 to-blue-50 rounded-2xl p-4 border-2 border-blue-200 overflow-hidden">
      {/* Casa Header */}
      <View className="flex-row items-center justify-center mb-4 pb-3 border-b-2 border-blue-200">
        <Ionicons name="home" size={28} color="#3B82F6" />
        <ThemedText className="text-xl font-bold text-slate-900 ml-2">Mi Casa</ThemedText>
        <ThemedText className="text-xs text-text-secondary ml-auto">{floors.length} pisos</ThemedText>
      </View>

      {/* Floors List */}
      <ScrollView
        showsVerticalScrollIndicator={false}
        scrollEnabled={true}
        nestedScrollEnabled={true}
        className="max-h-96"
      >
        {floors.map((floor) => (
          <View key={floor.id} className="mb-2">
            {/* Floor Accordion Header */}
            <TouchableOpacity
              onPress={() => toggleFloor(floor.id)}
              className="bg-white rounded-lg p-2 flex-row items-center justify-between border border-blue-300 mb-1"
            >
              <View className="flex-row items-center flex-1">
                <Ionicons
                  name={expandedFloors.has(floor.id) ? 'chevron-down' : 'chevron-forward'}
                  size={20}
                  color="#3B82F6"
                />
                <ThemedText className="text-sm font-semibold text-slate-900 ml-2">
                  {floor.name}
                </ThemedText>
                <ThemedText className="text-xs text-text-secondary ml-2">
                  ({floor.rooms.length} hab.)
                </ThemedText>
              </View>
              <TouchableOpacity
                onPress={(e) => {
                  e.stopPropagation();
                  onAddRoom?.();
                }}
              >
                <Ionicons name="add" size={18} color="#3B82F6" />
              </TouchableOpacity>
            </TouchableOpacity>

            {/* Floor Content - Rooms Grid */}
            {expandedFloors.has(floor.id) && (
              <View className="bg-blue-50 rounded-lg p-2 border border-blue-200">
                <RoomGrid
                  floorId={floor.id}
                  floorName=""
                  rooms={floor.rooms}
                  onRoomPress={onRoomPress}
                  onAddRoom={onAddRoom}
                />
              </View>
            )}
          </View>
        ))}
      </ScrollView>
    </View>
  );
};
