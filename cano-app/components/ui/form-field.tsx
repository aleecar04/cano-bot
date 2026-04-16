import { KeyboardTypeOptions, Text, TextInput, View } from 'react-native';

type Props = {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
  keyboardType?: KeyboardTypeOptions;
  editable?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
};

export function FormField({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry,
  keyboardType,
  editable = true,
  autoCapitalize = 'none',
}: Readonly<Props>) {
  return (
    <View className="gap-1.5">
      <Text className="text-text-secondary text-xs uppercase tracking-widest">
        {label}
      </Text>
      <TextInput
        className={`border border-border rounded-xl px-4 py-3.5 text-text text-sm ${
          editable ? 'bg-bg' : 'bg-bg-secondary'
        }`}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#94a3b8"
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        editable={editable}
        autoCapitalize={autoCapitalize}
      />
    </View>
  );
}