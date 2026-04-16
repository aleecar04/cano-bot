export const DEVICE_ICON_MAP: Record<string, string> = {
  SmartTV: 'tv',
  light: 'bulb',
  Luz: 'bulb',
  switch: 'toggle',
  climate: 'thermometer',
  Termostato: 'thermometer',
  IoT: 'hardware-chip',
  cover: 'layers',
  media_player: 'musical-notes',
  Altavoz: 'musical-notes',
  sensor: 'pulse',
  camera: 'videocam',
};

export function deviceIcon(type: string): string {
  return DEVICE_ICON_MAP[type] ?? 'cube-outline';
}
