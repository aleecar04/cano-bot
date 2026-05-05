export const DEVICE_ICON_MAP: Record<string, string> = {
  SmartTV:      'tv-outline',
  Luz:          'bulb-outline',
  IoT:          'hardware-chip-outline',
  Enchufe:      'flash-outline',
  Sensor:       'thermometer-outline',
  Termostato:   'thermometer-outline',
  Ordenador:    'desktop-outline',
  Impresora:    'print-outline',
  Altavoz:      'volume-medium-outline',
  Camara:       'videocam-outline',
  // Home Assistant domain types
  light:        'bulb-outline',
  switch:       'toggle-outline',
  climate:      'thermometer-outline',
  cover:        'layers-outline',
  media_player: 'musical-notes-outline',
  sensor:       'pulse-outline',
  camera:       'videocam-outline',
};

const DEVICE_COLOR_MAP: Record<string, string> = {
  SmartTV:      '#8b5cf6',
  Luz:          '#f59e0b',
  IoT:          '#3b82f6',
  Enchufe:      '#f97316',
  Sensor:       '#06b6d4',
  Termostato:   '#ef4444',
  Ordenador:    '#64748b',
  Impresora:    '#64748b',
  Altavoz:      '#10b981',
  Camara:       '#64748b',
  light:        '#f59e0b',
  switch:       '#3b82f6',
  climate:      '#ef4444',
  cover:        '#10b981',
  media_player: '#8b5cf6',
  sensor:       '#06b6d4',
  camera:       '#64748b',
};

export function deviceIcon(type: string): string {
  return DEVICE_ICON_MAP[type] ?? 'cube-outline';
}

export function deviceColor(type: string): string {
  return DEVICE_COLOR_MAP[type] ?? '#94a3b8';
}
