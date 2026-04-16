import { Modal, View, Text, TouchableOpacity } from 'react-native';

type Props = {
  visible: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmModal({
  visible,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  destructive = false,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <View className="flex-1 bg-black/50 items-center justify-center px-8">
        <View className="bg-bg-secondary border border-border rounded-2xl w-full max-w-sm overflow-hidden">
          <View className="px-6 pt-6 pb-4">
            <Text className="text-text text-base font-bold text-center">{title}</Text>
            {message && (
              <Text className="text-text-secondary text-sm text-center mt-2 leading-5">
                {message}
              </Text>
            )}
          </View>

          <View className="border-t border-border flex-row">
            <TouchableOpacity
              className="flex-1 py-4 items-center border-r border-border"
              onPress={onCancel}
              activeOpacity={0.7}
            >
              <Text className="text-text font-semibold text-sm">{cancelLabel}</Text>
            </TouchableOpacity>
            <TouchableOpacity
              className="flex-1 py-4 items-center"
              onPress={onConfirm}
              activeOpacity={0.7}
            >
              <Text className={`font-semibold text-sm ${destructive ? 'text-red-500' : 'text-primary'}`}>
                {confirmLabel}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}
