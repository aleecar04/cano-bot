import React, { useState } from 'react';
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  ScrollView, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type RoomDto } from '@/api/houses';
import { type VincularDeviceParams } from '@/api/devices';

interface ScannedDevice {
  ip: string;
  mac: string;
  hostname?: string;
  tipo?: string;
}

interface LinkDeviceModalProps {
  visible: boolean;
  device: ScannedDevice;
  rooms: RoomDto[];
  linking: boolean;
  onClose: () => void;
  onConfirm: (params: VincularDeviceParams) => void;
}

const TUYA_TYPES = new Set(['Luz', 'IoT', 'Termostato', 'light', 'switch', 'climate']);

export function LinkDeviceModal({
  visible,
  device,
  rooms,
  linking,
  onClose,
  onConfirm,
}: Readonly<LinkDeviceModalProps>) {
  const [name, setName] = useState(device.hostname ?? device.ip);
  const [selectedRoom, setSelectedRoom] = useState<string | undefined>(undefined);
  const [tuyaDevId, setTuyaDevId]         = useState('');
  const [tuyaLocalKey, setTuyaLocalKey]   = useState('');
  const [tuyaVersion, setTuyaVersion]     = useState<number>(3.4);

  const isTuya = TUYA_TYPES.has(device.tipo ?? '');

  const handleConfirm = () => {
    const config: Record<string, unknown> = isTuya
      ? { dev_id: tuyaDevId.trim(), local_key: tuyaLocalKey.trim(), channel: 0, version: tuyaVersion }
      : {};
    onConfirm({
      ip:       device.ip,
      mac:      device.mac,
      hostname: device.hostname ?? device.ip,
      tipo:     device.tipo ?? '',
      name:     name.trim() || device.hostname || device.ip,
      room_id:  selectedRoom,
      config,
    });
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={() => { if (!linking) onClose(); }}
    >
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary rounded-t-3xl border-t border-border pb-8">
          {/* Header */}
          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <Text className="text-text text-base font-bold">Vincular dispositivo</Text>
            <TouchableOpacity onPress={onClose} disabled={linking} activeOpacity={0.7}>
              <Ionicons name="close" size={22} color="#94a3b8" />
            </TouchableOpacity>
          </View>

          <ScrollView className="px-5 pt-4" showsVerticalScrollIndicator={false}>
            {/* Device info */}
            <View className="bg-bg border border-border rounded-xl px-4 py-3 mb-5">
              <Text className="text-text-secondary text-xs mb-1">IP detectada</Text>
              <Text className="text-text font-semibold">{device.ip}</Text>
              {!!device.mac && (
                <Text className="text-text-secondary text-xs mt-1">{device.mac}</Text>
              )}
              {!!device.tipo && (
                <Text className="text-indigo-400 text-xs mt-1">{device.tipo}</Text>
              )}
            </View>

            {/* Name input */}
            <Text className="text-text text-sm font-semibold mb-2">Nombre</Text>
            <TextInput
              className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm mb-5"
              value={name}
              onChangeText={setName}
              placeholder="Nombre del dispositivo"
              placeholderTextColor="#64748b"
              editable={!linking}
            />

            {/* Tuya credentials */}
            {isTuya && (
              <View className="bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3 mb-5">
                <View className="flex-row items-center gap-2 mb-3">
                  <Ionicons name="key-outline" size={14} color="#f59e0b" />
                  <Text className="text-amber-400 text-xs font-semibold">Credenciales Tuya</Text>
                </View>
                <Text className="text-text-secondary text-xs mb-3 leading-4">
                  Obtén estos datos en <Text className="text-amber-400">iot.tuya.com</Text> ejecutando{' '}
                  <Text className="font-mono text-amber-400">python -m tinytuya wizard</Text>
                </Text>
                <Text className="text-text text-xs font-semibold mb-1.5">Device ID</Text>
                <TextInput
                  className="bg-bg border border-border rounded-xl px-3 py-2.5 text-text text-sm mb-3 font-mono"
                  value={tuyaDevId}
                  onChangeText={setTuyaDevId}
                  placeholder="bf3a..."
                  placeholderTextColor="#475569"
                  editable={!linking}
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <Text className="text-text text-xs font-semibold mb-1.5">Local Key</Text>
                <TextInput
                  className="bg-bg border border-border rounded-xl px-3 py-2.5 text-text text-sm font-mono"
                  value={tuyaLocalKey}
                  onChangeText={setTuyaLocalKey}
                  placeholder="a1b2c3d4e5f6..."
                  placeholderTextColor="#475569"
                  editable={!linking}
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <Text className="text-text text-xs font-semibold mt-3 mb-1.5">Versión de protocolo</Text>
                <View className="flex-row gap-2 mb-1">
                  {[3.1, 3.3, 3.4, 3.5].map((v) => (
                    <TouchableOpacity
                      key={v}
                      onPress={() => setTuyaVersion(v)}
                      disabled={linking}
                      className={`px-3 py-1.5 rounded-lg border ${
                        tuyaVersion === v
                          ? 'bg-amber-500 border-amber-500'
                          : 'bg-bg border-border'
                      }`}
                    >
                      <Text className={`text-xs font-semibold ${tuyaVersion === v ? 'text-white' : 'text-text-secondary'}`}>
                        v{v}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <Text className="text-text-secondary text-xs leading-4">
                  La mayoría de dispositivos modernos usan v3.4. Si no sabes cuál tienes, prueba con v3.4 primero.
                </Text>
              </View>
            )}

            {/* Room selector */}
            {rooms.length > 0 && (
              <>
                <Text className="text-text text-sm font-semibold mb-2">Habitación</Text>
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  className="mb-5"
                >
                  <View className="flex-row gap-2 pr-4">
                    <TouchableOpacity
                      onPress={() => setSelectedRoom(undefined)}
                      className={`px-3 py-2 rounded-lg border ${
                        !selectedRoom
                          ? 'bg-indigo-500 border-indigo-500'
                          : 'bg-bg border-border'
                      }`}
                      activeOpacity={0.7}
                    >
                      <Text className={`text-xs font-semibold ${!selectedRoom ? 'text-white' : 'text-text-secondary'}`}>
                        Sin habitación
                      </Text>
                    </TouchableOpacity>
                    {rooms.map((room) => (
                      <TouchableOpacity
                        key={room.id}
                        onPress={() => setSelectedRoom(room.id)}
                        className={`px-3 py-2 rounded-lg border ${
                          selectedRoom === room.id
                            ? 'bg-indigo-500 border-indigo-500'
                            : 'bg-bg border-border'
                        }`}
                        activeOpacity={0.7}
                      >
                        <Text className={`text-xs font-semibold ${
                          selectedRoom === room.id ? 'text-white' : 'text-text-secondary'
                        }`}>
                          {room.name}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </ScrollView>
              </>
            )}

          </ScrollView>

          {/* Actions */}
          <View className="flex-row gap-3 px-5 pt-2">
            <TouchableOpacity
              className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
              onPress={onClose}
              disabled={linking}
              activeOpacity={0.7}
            >
              <Text className="text-text font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${
                linking || (isTuya && (!tuyaDevId.trim() || !tuyaLocalKey.trim()))
                  ? 'bg-indigo-500/60'
                  : 'bg-indigo-500'
              }`}
              onPress={handleConfirm}
              disabled={linking || (isTuya && (!tuyaDevId.trim() || !tuyaLocalKey.trim()))}
              activeOpacity={0.8}
            >
              {linking ? (
                <ActivityIndicator color="white" size="small" />
              ) : (
                <Ionicons name="link" size={16} color="white" />
              )}
              <Text className="text-text font-semibold text-sm">
                {linking ? 'Vinculando...' : 'Vincular'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}
