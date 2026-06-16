import { useState } from 'react';
import { KeyboardTypeOptions, Platform, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type Props = {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  secureTextEntry?: boolean;
  keyboardType?: KeyboardTypeOptions;
  editable?: boolean;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  maxLength?: number;
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
  maxLength,
}: Readonly<Props>) {
  const [hidden, setHidden] = useState(true);

  return (
    <View className="gap-1.5">
      <Text className="text-text-secondary text-xs uppercase tracking-widest">
        {label}
      </Text>
      <View
        className={`flex-row items-center border border-border rounded-xl ${
          editable ? 'bg-bg' : 'bg-bg-secondary'
        }`}
      >
        <TextInput
          className="flex-1 px-4 py-3.5 text-text text-sm"
          style={Platform.OS === 'web' ? { fontSize: 16 } : undefined}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor="#94a3b8"
          secureTextEntry={secureTextEntry && hidden}
          keyboardType={keyboardType}
          editable={editable}
          autoCapitalize={autoCapitalize}
          maxLength={maxLength}
        />
        {secureTextEntry && (
          <TouchableOpacity
            onPress={() => setHidden((h) => !h)}
            className="px-3 py-3.5"
            hitSlop={8}
            activeOpacity={0.7}
          >
            <Ionicons name={hidden ? 'eye-outline' : 'eye-off-outline'} size={20} color="#94a3b8" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}
