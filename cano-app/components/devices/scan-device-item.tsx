import React from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// Types with no home-automation use case — show as non-linkable
const NON_LINKABLE_TYPES = new Set(['Ordenador', 'Movil', 'Impresora', 'Router']);

// Types that are smart devices but need Home Assistant to be controlled
// Altavoz included: Alexa/Sonos/HomePod are not Tuya-compatible
const SUGGEST_HA_TYPES = new Set(['Camara', 'Dispositivo', 'Altavoz']);

interface Device {
  ip: string;
  mac: string;
  hostname?: string;
  tipo?: string;
  name?: string;
  location?: string;
  driver?: string;
}

interface ScanDeviceItemProps {
  device: Device;
  onLink: (device: Device) => void;
  isLinking: boolean;
  isLinked?: boolean;
}

export const ScanDeviceItem: React.FC<ScanDeviceItemProps> = ({ device, onLink, isLinking, isLinked = false }) => {
  const nonLinkable  = NON_LINKABLE_TYPES.has(device.tipo ?? '');
  const suggestHA    = SUGGEST_HA_TYPES.has(device.tipo ?? '');

  return (
    <View className={`border rounded-lg p-3 mb-2 flex-row items-center justify-between ${
      isLinked || nonLinkable ? 'bg-bg/50 border-border/50' : 'bg-bg-secondary border-border'
    }`}>
      <View className="flex-1">
        <Text className={`font-semibold text-sm ${isLinked || nonLinkable ? 'text-text-secondary' : 'text-text'}`}>
          {device.hostname || device.ip}
        </Text>
        <Text className="text-text-secondary text-xs">{device.ip}</Text>
        <View className="flex-row items-center gap-2 mt-0.5 flex-wrap">
          {device.tipo && (
            <Text className={`text-xs ${isLinked || nonLinkable ? 'text-text-secondary' : 'text-indigo-400'}`}>
              {device.tipo}
            </Text>
          )}
          {suggestHA && !isLinked && (
            <View className="bg-amber-500/20 rounded px-1.5 py-0.5 flex-row items-center gap-1">
              <Ionicons name="home-outline" size={10} color="#f59e0b" />
              <Text className="text-amber-400 text-xs font-semibold">Requiere HA</Text>
            </View>
          )}
        </View>
      </View>

      {isLinked && (
        <View className="rounded-lg px-3 py-2 flex-row items-center gap-1 bg-bg-secondary">
          <Ionicons name="checkmark-circle" size={14} color="#64748b" />
          <Text className="text-text-secondary text-xs font-semibold">Vinculado</Text>
        </View>
      )}
      {!isLinked && nonLinkable && (
        <View className="rounded-lg px-3 py-2 bg-bg/50">
          <Text className="text-text-secondary text-xs font-semibold">No compatible</Text>
        </View>
      )}
      {!isLinked && !nonLinkable && (
        <TouchableOpacity
          className={`rounded-lg px-3 py-2 flex-row items-center gap-1 ${
            isLinking ? 'bg-indigo-500/50' : 'bg-indigo-500'
          }`}
          onPress={() => onLink(device)}
          disabled={isLinking}
          activeOpacity={0.7}
        >
          {isLinking
            ? <ActivityIndicator color="white" size="small" />
            : <Ionicons name="link" size={14} color="white" />
          }
          <Text className="text-white text-xs font-semibold">
            {isLinking ? 'Vinculando...' : 'Vincular'}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
};
