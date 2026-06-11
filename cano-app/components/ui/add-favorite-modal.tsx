import { useState } from 'react';
import { Modal, View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { type DeviceDto } from '@/api/devices';
import { deviceIcon } from '@/utils/device-icons';
import {
  getActionsForType, actionNeedsPayload,
  LUZ_COLORES, TV_APPS, TV_VOLUMES,
  BRIGHTNESS_PRESETS, TEMP_PRESETS, kelvinToHex,
  type ActionDef,
} from '@/utils/device-actions';

type Step = 'device' | 'action' | 'payload' | 'name';

interface AddFavoriteModalProps {
  visible: boolean;
  devices: DeviceDto[];
  saving: boolean;
  onClose: () => void;
  onSelectAction: (device: DeviceDto, action: string, label: string, payload: Record<string, unknown>) => void;
}

export function AddFavoriteModal({
  visible, devices, saving, onClose, onSelectAction,
}: Readonly<AddFavoriteModalProps>) {
  const [step, setStep]                   = useState<Step>('device');
  const [pendingDevice, setPendingDevice] = useState<DeviceDto | null>(null);
  const [pendingAction, setPendingAction] = useState<ActionDef | null>(null);
  const [pendingPayload, setPendingPayload] = useState<Record<string, unknown>>({});
  const [customLabel, setCustomLabel]     = useState('');

  // payload state — presets only
  const [brightnessVal, setBrightnessVal] = useState(75);
  const [colorTempVal, setColorTempVal]   = useState(4000);
  const [volumeVal, setVolumeVal]         = useState(50);
  const [selectedApp, setSelectedApp]     = useState('netflix');
  const [selectedColor, setSelectedColor] = useState('rojo'); // color name

  const isTuya      = pendingDevice?.driver === 'tuya';
  const actionItems = getActionsForType(pendingDevice?.type ?? '', isTuya);

  const resetAndClose = () => {
    setStep('device');
    setPendingDevice(null);
    setPendingAction(null);
    setPendingPayload({});
    setCustomLabel('');
    onClose();
  };

  const _goToName = (action: ActionDef, payload: Record<string, unknown>) => {
    setPendingPayload(payload);
    setCustomLabel(action.label);  // prefill con la etiqueta de la acción; el usuario puede renombrar
    setStep('name');
  };

  const handleSelectDevice = (device: DeviceDto) => {
    setPendingDevice(device);
    setStep('action');
  };

  const handleSelectAction = (action: ActionDef) => {
    setPendingAction(action);
    if (!actionNeedsPayload(action)) {
      _goToName(action, {});
      return;
    }
    setStep('payload');
  };

  const handleConfirmPayload = () => {
    if (!pendingAction) return;
    let payload: Record<string, unknown> = {};
    switch (pendingAction.payloadType) {
      case 'brightness': payload = { value: brightnessVal }; break;
      case 'color_temp': payload = { value: colorTempVal }; break;
      case 'volumen':    payload = { value: volumeVal }; break;
      case 'app':        payload = { app: selectedApp }; break;
      case 'color':      payload = { color: selectedColor }; break;
    }
    _goToName(pendingAction, payload);
  };

  const handleConfirmName = () => {
    if (!pendingAction || !pendingDevice) return;
    const label = customLabel.trim() || pendingAction.label;
    onSelectAction(pendingDevice, pendingAction.action, label, pendingPayload);
  };

  const handleBack = () => {
    if (step === 'name') { setStep(actionNeedsPayload(pendingAction!) ? 'payload' : 'action'); }
    else if (step === 'payload') { setStep('action'); setPendingAction(null); }
    else if (step === 'action') { setStep('device'); setPendingDevice(null); }
  };

  const STEP_TITLES: Record<Step, string> = {
    device:  'Selecciona dispositivo',
    action:  'Selecciona acción',
    payload: 'Configura valor',
    name:    'Nombra tu favorito',
  };
  const title = STEP_TITLES[step];

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={resetAndClose}>
      <View className="flex-1 bg-black/60 justify-end">
        <View className="bg-bg-secondary rounded-t-3xl border-t border-border pb-8">

          {/* Header */}
          <View className="flex-row items-center justify-between px-5 pt-5 pb-4 border-b border-border">
            <View>
              <Text className="text-text text-base font-bold">{title}</Text>
              {step !== 'device' && !!pendingDevice && (
                <Text className="text-text-secondary text-xs mt-0.5">{pendingDevice.name}</Text>
              )}
            </View>
            <View className="flex-row items-center gap-3">
              {step !== 'device' && (
                <TouchableOpacity onPress={handleBack} disabled={saving}>
                  <Ionicons name="arrow-back" size={20} color="#94a3b8" />
                </TouchableOpacity>
              )}
              <TouchableOpacity onPress={resetAndClose} disabled={saving}>
                <Ionicons name="close" size={22} color="#94a3b8" />
              </TouchableOpacity>
            </View>
          </View>

          <ScrollView className="px-5 pt-4" style={{ maxHeight: 420 }} showsVerticalScrollIndicator={false}>

            {/* Step: device */}
            {step === 'device' && (
              devices.length === 0 ? (
                <View className="py-8 items-center">
                  <Text className="text-text-secondary text-sm">No tienes dispositivos vinculados</Text>
                </View>
              ) : (
                devices.map((d) => (
                  <TouchableOpacity key={d.id} onPress={() => handleSelectDevice(d)} activeOpacity={0.7}
                    className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-2">
                    <Ionicons name={deviceIcon(d.type) as any} size={20} color="#94a3b8" />
                    <View className="flex-1">
                      <Text className="text-text font-semibold text-sm">{d.name}</Text>
                      <Text className="text-text-secondary text-xs">{d.type}</Text>
                    </View>
                    <View className={`px-2 py-0.5 rounded-full ${d.is_online ? 'bg-green-500/15' : 'bg-bg'}`}>
                      <Text className={`text-xs font-semibold ${d.is_online ? 'text-green-400' : 'text-text-secondary'}`}>
                        {d.is_online ? 'Online' : 'Offline'}
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))
              )
            )}

            {/* Step: action */}
            {step === 'action' && actionItems.map((a) => (
              <TouchableOpacity key={a.action} onPress={() => handleSelectAction(a)} disabled={saving} activeOpacity={0.7}
                className="flex-row items-center gap-3 bg-bg border border-border rounded-xl px-4 py-3 mb-2">
                {saving
                  ? <ActivityIndicator size="small" color="#6366f1" />
                  : <Ionicons name={a.icon as any} size={20} color="#6366f1" />}
                <Text className="text-text font-semibold text-sm flex-1">{a.label}</Text>
                {actionNeedsPayload(a) && <Ionicons name="chevron-forward" size={16} color="#64748b" />}
              </TouchableOpacity>
            ))}

            {/* Step: payload */}
            {step === 'payload' && pendingAction && (
              <View className="py-2">

                {/* Brillo */}
                {pendingAction.payloadType === 'brightness' && (
                  <View>
                    <Text className="text-text text-sm font-semibold mb-3">Nivel de brillo</Text>
                    <View className="flex-row gap-2">
                      {BRIGHTNESS_PRESETS.map((v) => (
                        <TouchableOpacity key={v} onPress={() => setBrightnessVal(v)} activeOpacity={0.7}
                          className={`flex-1 py-3 rounded-lg border items-center ${brightnessVal === v ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}>
                          <Text className={`text-sm font-bold ${brightnessVal === v ? 'text-indigo-400' : 'text-text-secondary'}`}>{v}%</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}

                {/* Temperatura */}
                {pendingAction.payloadType === 'color_temp' && (
                  <View>
                    <Text className="text-text text-sm font-semibold mb-3">Temperatura de color</Text>
                    <View style={{ height: 16, borderRadius: 8, backgroundColor: kelvinToHex(colorTempVal), marginBottom: 10 }} />
                    <View className="flex-row gap-2">
                      {TEMP_PRESETS.map(({ label, value, color }) => (
                        <TouchableOpacity key={value} onPress={() => setColorTempVal(value)} activeOpacity={0.7}
                          className={`flex-1 py-3 rounded-lg border items-center ${colorTempVal === value ? 'border-indigo-500/60 bg-indigo-500/20' : 'border-border bg-bg'}`}>
                          <View style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: color, marginBottom: 4 }} />
                          <Text className={`text-xs font-semibold ${colorTempVal === value ? 'text-indigo-400' : 'text-text-secondary'}`}>{label}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}

                {/* Color */}
                {pendingAction.payloadType === 'color' && (
                  <View>
                    <Text className="text-text text-sm font-semibold mb-3">Color</Text>
                    {(() => {
                      const cur = LUZ_COLORES.find((c) => c.name === selectedColor);
                      return cur ? (
                        <View className="flex-row items-center gap-2 mb-3">
                          <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: cur.hex, borderWidth: 2, borderColor: 'rgba(255,255,255,0.35)' }} />
                          <View style={{ flex: 1, height: 14, borderRadius: 7, backgroundColor: cur.hex, opacity: 0.55 }} />
                        </View>
                      ) : null;
                    })()}
                    <View className="flex-row flex-wrap gap-3 justify-center">
                      {LUZ_COLORES.map(({ name, hex }) => {
                        const isActive = selectedColor === name;
                        return (
                          <TouchableOpacity key={name} onPress={() => setSelectedColor(name)} activeOpacity={0.7}
                            style={{ width: isActive ? 44 : 36, height: isActive ? 44 : 36, borderRadius: isActive ? 22 : 18, backgroundColor: hex, borderWidth: isActive ? 3 : 2, borderColor: isActive ? 'white' : 'rgba(255,255,255,0.2)' }} />
                        );
                      })}
                    </View>
                  </View>
                )}

                {/* Volumen */}
                {pendingAction.payloadType === 'volumen' && (
                  <View>
                    <Text className="text-text text-sm font-semibold mb-3">Nivel de volumen</Text>
                    <View className="flex-row flex-wrap gap-2">
                      {TV_VOLUMES.map((v) => (
                        <TouchableOpacity key={v} onPress={() => setVolumeVal(v)} activeOpacity={0.7}
                          className={`px-4 py-2 rounded-lg border ${volumeVal === v ? 'bg-indigo-500 border-indigo-500' : 'bg-bg border-border'}`}>
                          <Text className={`text-sm font-bold ${volumeVal === v ? 'text-white' : 'text-text-secondary'}`}>{v}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}

                {/* App */}
                {pendingAction.payloadType === 'app' && (
                  <View>
                    <Text className="text-text text-sm font-semibold mb-3">Aplicación</Text>
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

                <TouchableOpacity className="mt-6 bg-indigo-500 rounded-xl py-3 items-center flex-row justify-center gap-2"
                  onPress={handleConfirmPayload} disabled={saving} activeOpacity={0.8}>
                  <Ionicons name="arrow-forward" size={16} color="white" />
                  <Text className="text-white font-semibold text-sm">Siguiente</Text>
                </TouchableOpacity>

              </View>
            )}

            {/* Step: name */}
            {step === 'name' && pendingAction && (
              <View className="py-2">
                <Text className="text-text text-sm font-semibold mb-2">Nombre del favorito</Text>
                <Text className="text-text-secondary text-xs mb-3">
                  Así se mostrará en tu panel. Puedes dejarlo como está o ponerle uno propio.
                </Text>
                <TextInput
                  className="bg-bg border border-border rounded-xl px-4 py-3 text-text text-sm"
                  style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
                  value={customLabel}
                  onChangeText={setCustomLabel}
                  placeholder={pendingAction.label}
                  placeholderTextColor="#475569"
                  maxLength={50}
                  editable={!saving}
                  autoFocus
                />

                <TouchableOpacity className="mt-6 bg-indigo-500 rounded-xl py-3 items-center flex-row justify-center gap-2"
                  onPress={handleConfirmName} disabled={saving} activeOpacity={0.8}>
                  {saving
                    ? <ActivityIndicator color="white" size="small" />
                    : <Ionicons name="checkmark" size={16} color="white" />}
                  <Text className="text-white font-semibold text-sm">{saving ? 'Guardando...' : 'Guardar favorito'}</Text>
                </TouchableOpacity>
              </View>
            )}

          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
