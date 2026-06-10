import { ActivityIndicator, Text, TouchableOpacity } from 'react-native';

type Props = {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger';
};

export function Button({ label, onPress, loading, disabled, variant = 'primary' }: Readonly<Props>) {
  const containerStyles = {
    primary: loading || disabled ? 'bg-primary/60' : 'bg-primary',
    secondary: 'bg-bg-secondary border border-border',
    danger: 'bg-red-500',
  };

  const textStyles = {
    primary: 'text-white',
    secondary: 'text-text',
    danger: 'text-white',
  };

  return (
    <TouchableOpacity
      className={`rounded-xl py-4 items-center ${containerStyles[variant]}`}
      onPress={onPress}
      disabled={loading || disabled}
      activeOpacity={0.8}
    >
      {loading
        ? <ActivityIndicator color="white" />
        : <Text className={`font-semibold text-sm tracking-wide ${textStyles[variant]}`}>
            {label}
          </Text>
      }
    </TouchableOpacity>
  );
}