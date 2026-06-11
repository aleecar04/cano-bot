import { useRef, useState } from 'react';
import {
  View, Text, TouchableOpacity, Modal,
  ScrollView, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { vincularDevice, waitForDeviceStatus, scanNetwork, waitForCommand, type DeviceDto, type VincularDeviceParams } from '@/api/devices';
import { getMyRooms, type RoomDto } from '@/api/houses';
import { friendlyError } from '@/utils/friendly-error';
import { ScanDeviceItem } from '@/components/devices/scan-device-item';
import { LinkedDeviceItem } from '@/components/devices/linked-device-item';
import { DeviceEmptyState } from '@/components/devices/device-empty-state';
import { LinkDeviceModal } from '@/components/devices/link-device-modal';
import { ConfirmModal } from '@/components/ui/confirm-modal';

interface ScannedDevice {
  ip: string;
  mac: string;
  hostname?: string;
  tipo?: string;
}

interface Props {
  linkedDevices: DeviceDto[];
  loadingDevices: boolean;
  onLinkSuccess: (device: DeviceDto) => void;
  onUnlinkSuccess: (deviceId: string) => void;
  onEditSuccess: (device: DeviceDto) => void;
  onDeviceUpdate: (updated: DeviceDto) => void;
  onToast: (message: string, variant: 'success' | 'error') => void;
}

export function DevicesTab({
  linkedDevices, loadingDevices,
  onLinkSuccess, onUnlinkSuccess, onEditSuccess, onDeviceUpdate, onToast,
}: Readonly<Props>) {
  const [scanning, setScanning]             = useState(false);
  const [scannedDevices, setScannedDevices] = useState<ScannedDevice[]>([]);
  const [showScanModal, setShowScanModal]   = useState(false);
  const scanCancelledRef                    = useRef(false);
  const [pendingDevice, setPendingDevice]   = useState<ScannedDevice | null>(null);
  const [rooms, setRooms]                   = useState<RoomDto[]>([]);
  const [showLinkModal, setShowLinkModal]   = useState(false);
  const [linking, setLinking]               = useState(false);
  const [unlinkTarget, setUnlinkTarget]     = useState<{ id: string; name: string } | null>(null);

  const handleScanDevices = async () => {
    scanCancelledRef.current = false;
    setScanning(true);
    setScannedDevices([]);
    setShowScanModal(true);
    try {
      const { command_id } = await scanNetwork();
      const command = await waitForCommand(command_id);
      if (scanCancelledRef.current) return;
      if (command.status === 'failed') throw new Error(command.error ?? 'Error al escanear');
      const data = (command.result_data ?? {}) as { dispositivos?: ScannedDevice[] };
      if (Array.isArray(data.dispositivos)) {
        setScannedDevices(data.dispositivos);
      }
    } catch (err) {
      if (scanCancelledRef.current) return;
      const msg = String(err).includes('timeout')
        ? 'El escaneo tardó demasiado. Asegúrate de que el asistente está activo e inténtalo de nuevo.'
        : friendlyError(err);
      onToast(msg, 'error');
      setShowScanModal(false);
    } finally {
      if (!scanCancelledRef.current) setScanning(false);
    }
  };

  const cancelScan = () => {
    scanCancelledRef.current = true;
    setScanning(false);
    setShowScanModal(false);
  };

  const handleOpenLinkModal = async (device: ScannedDevice) => {
    if (linkedDevices.some((d) => d.ip === device.ip)) return;
    try {
      const roomList = await getMyRooms();
      setRooms(roomList);
    } catch {
      setRooms([]);
    }
    setPendingDevice(device);
    setShowLinkModal(true);
  };

  const handleConfirmLink = async (params: VincularDeviceParams) => {
    setLinking(true);
    try {
      const result = await vincularDevice(params);
      setShowLinkModal(false);
      setPendingDevice(null);
      onToast(`Comprobando ${params.name}…`, 'success');

      const updated = await waitForDeviceStatus(result.id);
      onLinkSuccess(updated);
      const estadoMsg = updated.is_online ? 'en línea' : 'sin conexión';
      onToast(`${params.name} listo — ${estadoMsg}`, updated.is_online ? 'success' : 'error');
    } catch (err) {
      onToast(friendlyError(err), 'error');
    } finally {
      setLinking(false);
    }
  };

  const handleConfirmUnlink = async () => {
    if (!unlinkTarget) return;
    const { id, name } = unlinkTarget;
    setUnlinkTarget(null);
    try {
      const { desvincularDevice } = await import('@/api/devices');
      await desvincularDevice(id);
      onUnlinkSuccess(id);
      onToast(`${name} desvinculado`, 'success');
    } catch (err) {
      onToast(friendlyError(err), 'error');
    }
  };

  const renderDevicesList = () => {
    if (loadingDevices) {
      return (
        <View className="py-12 items-center">
          <ActivityIndicator size="large" color="#3B82F6" />
        </View>
      );
    }
    if (linkedDevices.length === 0) {
      return <DeviceEmptyState />;
    }
    return (
      <View className="gap-3">
        {linkedDevices.map((device) => (
          <LinkedDeviceItem
            key={device.id}
            device={device}
            onUnlink={(id, name) => setUnlinkTarget({ id, name })}
            onDeviceUpdate={onDeviceUpdate}
            onEditSuccess={onEditSuccess}
          />
        ))}
      </View>
    );
  };

  return (
    <>
      {/* Scan section */}
      <View className="mb-6">
        <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-3">
          Descubrir dispositivos
        </Text>
        <TouchableOpacity
          className={`rounded-xl py-3.5 items-center flex-row justify-center gap-2 ${
            scanning ? 'bg-primary/60' : 'bg-primary'
          }`}
          onPress={handleScanDevices}
          disabled={scanning}
          activeOpacity={0.8}
        >
          {scanning
            ? <ActivityIndicator color="white" size="small" />
            : <Ionicons name="search" size={18} color="white" />
          }
          <Text className="text-white font-semibold text-sm">
            {scanning ? 'Escaneando...' : 'Escanear red'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Linked devices section */}
      <View>
        <View className="flex-row items-center justify-between mb-3">
          <Text className="text-text-secondary text-xs font-bold uppercase tracking-wider">
            Dispositivos vinculados
          </Text>
          <Text className="text-text-secondary text-xs">{linkedDevices.length} total</Text>
        </View>

        {/* Sync notice */}
        <View className="flex-row items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-2.5 mb-4">
          <Ionicons name="time-outline" size={13} color="#f59e0b" style={{ marginTop: 1 }} />
          <Text className="text-amber-400/80 text-xs flex-1 leading-4">
            El estado se sincroniza cada ~45 s. Acciones externas a la app pueden tardar hasta ese tiempo en reflejarse.
          </Text>
        </View>

        {renderDevicesList()}
      </View>

      {/* Scan results modal */}
      <Modal
        visible={showScanModal}
        transparent
        animationType="fade"
        onRequestClose={() => (scanning ? cancelScan() : setShowScanModal(false))}
      >
        <View className="flex-1 bg-black/50 justify-center items-center px-4">
          <View className="bg-bg-secondary rounded-2xl border border-border w-full max-w-md" style={{ height: '60%' }}>
            <View className="border-b border-border px-4 py-3 flex-row items-center justify-between">
              <View>
                <Text className="text-text text-base font-bold">
                  {scanning ? 'Escaneando red...' : 'Dispositivos encontrados'}
                </Text>
                {!scanning && scannedDevices.length > 0 && (
                  <Text className="text-text-secondary text-xs mt-0.5">{scannedDevices.length} dispositivos</Text>
                )}
              </View>
              <TouchableOpacity onPress={() => (scanning ? cancelScan() : setShowScanModal(false))}>
                <Ionicons name="close" size={22} color="#94a3b8" />
              </TouchableOpacity>
            </View>

            <ScrollView className="flex-1 px-4 py-3">
              {scanning && (
                <View className="py-20 items-center">
                  <ActivityIndicator size="large" color="#6366f1" />
                  <Text className="text-text-secondary text-sm mt-4">Buscando en tu red...</Text>
                </View>
              )}
              {!scanning && scannedDevices.length > 0 && scannedDevices.map((device) => (
                <ScanDeviceItem
                  key={device.ip}
                  device={device}
                  onLink={handleOpenLinkModal}
                  isLinking={false}
                  isLinked={linkedDevices.some((d) =>
                    d.ip === device.ip ||
                    (!!d.mac && !!device.mac && d.mac.toLowerCase() === device.mac.toLowerCase())
                  )}
                />
              ))}
              {!scanning && scannedDevices.length === 0 && (
                <View className="py-20 items-center">
                  <Ionicons name="search-outline" size={40} color="#94a3b8" />
                  <Text className="text-text-secondary text-sm text-center mt-3">No se encontraron dispositivos</Text>
                </View>
              )}
            </ScrollView>

            <View className="border-t border-border px-4 py-3 flex-row gap-3">
              <TouchableOpacity
                className="flex-1 bg-bg border border-border rounded-lg py-2.5 items-center"
                onPress={() => (scanning ? cancelScan() : setShowScanModal(false))}
              >
                <Text className="text-text font-semibold text-xs">{scanning ? 'Cancelar' : 'Cerrar'}</Text>
              </TouchableOpacity>
              {scannedDevices.length > 0 && !scanning && (
                <TouchableOpacity
                  className="flex-1 bg-indigo-500 rounded-lg py-2.5 items-center"
                  onPress={handleScanDevices}
                >
                  <Text className="text-white font-semibold text-xs">Escanear de nuevo</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        </View>
      </Modal>

      {pendingDevice && (
        <LinkDeviceModal
          visible={showLinkModal}
          device={pendingDevice}
          rooms={rooms}
          linking={linking}
          onClose={() => { setShowLinkModal(false); setPendingDevice(null); }}
          onConfirm={handleConfirmLink}
        />
      )}

      <ConfirmModal
        visible={unlinkTarget !== null}
        title="Desvincular dispositivo"
        message={`¿Desvincular ${unlinkTarget?.name}?`}
        confirmLabel="Desvincular"
        destructive
        onConfirm={handleConfirmUnlink}
        onCancel={() => setUnlinkTarget(null)}
      />
    </>
  );
}
