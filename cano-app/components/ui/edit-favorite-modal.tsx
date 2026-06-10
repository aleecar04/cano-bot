import { useState, useEffect } from 'react';
import { Modal, View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type FavoriteDto } from '@/api/favorites';
import { type DeviceDto } from '@/api/devices';
import {
  getActionsForType,
  LUZ_COLORES, TV_APPS, TV_VOLUMES,
  BRIGHTNESS_PRESETS, TEMP_PRESETS, kelvinToHex,
} from '@/utils/device-actions';

interface EditFavoriteModalProps {
  visible: boolean;
  favorite: FavoriteDto | null;
  devices: DeviceDto[];
  saving: boolean;
  onClose: () => void;
  onConfirm: (id: string, action: string, payload: Record<string, unknown>, label: string) => void;
}

export function EditFavoriteModal({ visible, favorite, devices, saving, onClose, onConfirm }: Readonly<EditFavoriteModalProps>) {
  const device     = devices.find((d) => d.id === favorite?.device_id) ?? null;
  const isTuya     = device?.driver === 'tuya';
  const actions    = getActionsForType(device?.type ?? '', isTuya);

  const [selectedAction, setSelectedAction] = useState('encender');
  const [label, setLabel]                   = useState('');
  const [brightnessVal, setBrightnessVal]   = useState(75);
  const [colorTempVal, setColorTempVal]     = useState(4000);
  const [volumeVal, setVolumeVal]           = useState(50);
  const [selectedApp, setSelectedApp]       = useState('netflix');
  const [selectedColor, setSelectedColor]   = useState('rojo');

  useEffect(() => {
    if (!visible || !favorite) return;
    setSelectedAction(favorite.action);
    setLabel(favorite.label ?? '');
    const p = favorite.payload ?? {};
    if (typeof p.valor === 'number') {
      if (BRIGHTNESS_PRESETS.includes(p.valor)) setBrightnessVal(p.valor);
      if (TEMP_PRESETS.some((t) => t.valor === p.valor)) setColorTempVal(p.valor);
      setVolumeVal(p.valor);
    }
    if (typeof p.app === 'string') setSelectedApp(p.app);
    if (typeof p.color === 'string') setSelectedColor(p.color);
  }, [visible, favorite]);

  const currentActionDef = actions.find((a) => a.accion === selectedAction);

  const buildPayload = (): Record<string, unknown> => {
    switch (currentActionDef?.payloadType) {
      case 'brightness': return { valor: brightnessVal };
      case 'color_temp': return { valor: colorTempVal };
      case 'volumen':    return { valor: volumeVal };
      case 'app':        return { app: selectedApp };
      case 'color':      return { color: selectedColor };
      default:           return {};
    }
  };

  const handleConfirm = () => {
    if (!favorite) return;
    const def       = actions.find((a) => a.accion === selectedAction);
    const autoLabel = label.trim() || `${def?.label ?? selectedAction} ${device?.name ?? ''}`;
    onConfirm(favorite.id, selectedAction, buildPayload(), autoLabel);
  };

  if (!favorite || !device) return null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={() => { if (!saving) onClose(); }}>
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary rounded-t-3xl border-t border-border pb-8">

          {/* Header */}
          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <View>
              <Text className="text-text text-base font-bold">Editar favorito</Text>
              <Text className="text-text-secondary text-xs mt-0.5">{device.name}</Text>
            </View>
            <TouchableOpacity onPress={onClose} disabled={saving} activeOpacity={0.7}>
              <Ionicons name="close" size={22} color="#94a3b8" />
            </TouchableOpacity>
          </View>

          <ScrollView className="px-5 pt-4" showsVerticalScrollIndicator={false} style={{ maxHeight: 480 }}>

            {/* Etiqueta */}
            <Text className="text-text text-sm font-semibold mb-2">Etiqueta (opcional)</Text>
            <TextInput
              className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm mb-5"
              style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
              value={label} onChangeText={setLabel}
              placeholder="Ej. Encender tele por la noche"
              placeholderTextColor="#64748b" editable={!saving}
              maxLength={50}
            />

            {/* Acción */}
            <Text className="text-text text-sm font-semibold mb-2">Acción</Text>
            <View className="flex-row flex-wrap gap-2 mb-5">
              {actions.map((a) => (
                <TouchableOpacity key={a.accion} onPress={() => setSelectedAction(a.accion)} activeOpacity={0.7}
                  className={`flex-row items-center gap-1.5 px-3 py-2 rounded-lg border ${selectedAction === a.accion ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                  <Ionicons name={a.icon as any} size={14} color={selectedAction === a.accion ? 'white' : '#94a3b8'} />
                  <Text className={`text-xs font-semibold ${selectedAction === a.accion ? 'text-white' : 'text-text-secondary'}`}>{a.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Brillo */}
            {currentActionDef?.payloadType === 'brightness' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Brillo</Text>
                <View className="flex-row gap-2">
                  {BRIGHTNESS_PRESETS.map((v) => (
                    <TouchableOpacity key={v} onPress={() => setBrightnessVal(v)} activeOpacity={0.7}
                      className={`flex-1 py-2 rounded-lg border items-center ${brightnessVal === v ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}>
                      <Text className={`text-xs font-semibold ${brightnessVal === v ? 'text-indigo-400' : 'text-text-secondary'}`}>{v}%</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* Temperatura */}
            {currentActionDef?.payloadType === 'color_temp' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Temperatura de color</Text>
                <View style={{ height: 14, borderRadius: 7, backgroundColor: kelvinToHex(colorTempVal), marginBottom: 8 }} />
                <View className="flex-row gap-2">
                  {TEMP_PRESETS.map(({ label: lbl, valor, color }) => (
                    <TouchableOpacity key={valor} onPress={() => setColorTempVal(valor)} activeOpacity={0.7}
                      className={`flex-1 py-2 rounded-lg border items-center ${colorTempVal === valor ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}>
                      <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: color, marginBottom: 3 }} />
                      <Text className={`text-xs font-semibold ${colorTempVal === valor ? 'text-indigo-400' : 'text-text-secondary'}`}>{lbl}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* Color */}
            {currentActionDef?.payloadType === 'color' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Color</Text>
                {(() => {
                  const cur = LUZ_COLORES.find((c) => c.name === selectedColor);
                  return cur ? (
                    <View className="flex-row items-center gap-2 mb-3">
                      <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: cur.hex, borderWidth: 2, borderColor: 'rgba(255,255,255,0.35)' }} />
                      <View style={{ flex: 1, height: 14, borderRadius: 7, backgroundColor: cur.hex, opacity: 0.55 }} />
                    </View>
                  ) : null;
                })()}
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View className="flex-row gap-2 pr-2">
                    {LUZ_COLORES.map(({ name, hex }) => {
                      const isActive = selectedColor === name;
                      return (
                        <TouchableOpacity key={name} onPress={() => setSelectedColor(name)} activeOpacity={0.7}
                          style={{ width: isActive ? 36 : 30, height: isActive ? 36 : 30, borderRadius: isActive ? 18 : 15, backgroundColor: hex, borderWidth: isActive ? 3 : 2, borderColor: isActive ? 'white' : 'rgba(255,255,255,0.2)' }} />
                      );
                    })}
                  </View>
                </ScrollView>
              </View>
            )}

            {/* Volumen */}
            {currentActionDef?.payloadType === 'volumen' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Volumen</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View className="flex-row gap-2 pr-4">
                    {TV_VOLUMES.map((v) => (
                      <TouchableOpacity key={v} onPress={() => setVolumeVal(v)} activeOpacity={0.7}
                        className={`px-3 py-2 rounded-lg border ${volumeVal === v ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                        <Text className={`text-xs font-bold ${volumeVal === v ? 'text-white' : 'text-text-secondary'}`}>{v}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </ScrollView>
              </View>
            )}

            {/* App */}
            {currentActionDef?.payloadType === 'app' && (
              <View className="mb-5">
                <Text className="text-text text-sm font-semibold mb-2">Aplicación</Text>
                {TV_APPS.map((ap) => (
                  <TouchableOpacity key={ap.app} onPress={() => setSelectedApp(ap.app)} activeOpacity={0.7}
                    className={`flex-row items-center gap-3 px-4 py-3 rounded-xl border mb-2 ${selectedApp === ap.app ? 'bg-indigo-500/20 border-indigo-500/50' : 'bg-bg border-border'}`}>
                    <Ionicons name={ap.icon as any} size={20} color={selectedApp === ap.app ? '#818cf8' : '#94a3b8'} />
                    <Text className={`text-sm font-semibold ${selectedApp === ap.app ? 'text-indigo-300' : 'text-text'}`}>{ap.label}</Text>
                    {selectedApp === ap.app && <Ionicons name="checkmark" size={16} color="#818cf8" style={{ marginLeft: 'auto' }} />}
                  </TouchableOpacity>
                ))}
              </View>
            )}

          </ScrollView>

          {/* Botones */}
          <View className="flex-row gap-3 px-5 pt-2">
            <TouchableOpacity className="flex-1 bg-bg border border-border rounded-xl py-3 items-center"
              onPress={onClose} disabled={saving} activeOpacity={0.7}>
              <Text className="text-text font-semibold text-sm">Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className={`flex-1 rounded-xl py-3 items-center flex-row justify-center gap-2 ${saving ? 'bg-indigo-500/40' : 'bg-indigo-500'}`}
              onPress={handleConfirm} disabled={saving} activeOpacity={0.8}>
              {saving ? <ActivityIndicator color="white" size="small" /> : <Ionicons name="checkmark" size={16} color="white" />}
              <Text className="text-text font-semibold text-sm">{saving ? 'Guardando...' : 'Guardar'}</Text>
            </TouchableOpacity>
          </View>

        </View>
      </View>
    </Modal>
  );
}
