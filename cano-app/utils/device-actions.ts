// Centralized action definitions for all device types.
// Import from here instead of defining per-file.

export type PayloadType = 'brightness' | 'color_temp' | 'volumen' | 'app' | 'color';

export interface ActionDef {
  action: string;
  icon: string;
  label: string;
  payloadType?: PayloadType;
}

// ── Shared data ───────────────────────────────────────────────────────────────

export const LUZ_COLORES: { name: string; hex: string }[] = [
  { name: 'rojo',     hex: '#FF2020' },
  { name: 'naranja',  hex: '#FF6400' },
  { name: 'amarillo', hex: '#FFC800' },
  { name: 'verde',    hex: '#00C800' },
  { name: 'cyan',     hex: '#00C8FF' },
  { name: 'azul',     hex: '#0000FF' },
  { name: 'morado',   hex: '#8000C8' },
  { name: 'violeta',  hex: '#9400D3' },
  { name: 'rosa',     hex: '#FF1493' },
  { name: 'blanco',   hex: '#FFFFFF' },
];

export const TV_APPS: { app: string; label: string; icon: string }[] = [
  { app: 'netflix', label: 'Netflix', icon: 'logo-netflix' },
  { app: 'youtube', label: 'YouTube', icon: 'logo-youtube' },
  { app: 'prime',   label: 'Prime',   icon: 'cart-outline' },
];

export const TV_VOLUMES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

export const BRIGHTNESS_PRESETS = [25, 50, 75, 100];

export const TEMP_PRESETS: { label: string; value: number; color: string }[] = [
  { label: 'Cálida', value: 2700, color: '#f97316' },
  { label: 'Neutra', value: 4000, color: '#fbbf24' },
  { label: 'Fría',   value: 6500, color: '#93c5fd' },
];

export function kelvinToHex(k: number): string {
  const c = Math.max(2700, Math.min(6500, k));
  if (c <= 4000) {
    const t = (c - 2700) / 1300;
    return `rgb(${Math.round(249 + t * 2)},${Math.round(115 + t * 76)},${Math.round(22 + t * 14)})`;
  }
  const t = (c - 4000) / 2500;
  return `rgb(${Math.round(251 - t * 104)},${Math.round(191 + t * 6)},${Math.round(36 + t * 217)})`;
}

export const BULB_TYPES      = new Set(['Luz', 'light']);
export const TUYA_BULB_TYPES = new Set(['Luz']);

// ── Action lists per device type ──────────────────────────────────────────────

const ON_OFF: ActionDef[] = [
  { action: 'encender', icon: 'power',         label: 'Encender' },
  { action: 'apagar',   icon: 'power-outline', label: 'Apagar' },
];

const TV_ACCIONES: ActionDef[] = [
  { action: 'encender',      icon: 'power',           label: 'Encender' },
  { action: 'apagar',        icon: 'power-outline',   label: 'Apagar' },
  { action: 'subir_volumen', icon: 'volume-high',     label: 'Vol +' },
  { action: 'bajar_volumen', icon: 'volume-low',      label: 'Vol -' },
  { action: 'mute',          icon: 'volume-mute',     label: 'Mute' },
  { action: 'set_volumen',   icon: 'options-outline', label: 'Volumen',   payloadType: 'volumen' },
  { action: 'abrir_app',     icon: 'apps-outline',    label: 'Abrir app', payloadType: 'app' },
];

const SPEAKER_ACCIONES: ActionDef[] = [
  { action: 'encender',      icon: 'power',           label: 'Encender' },
  { action: 'apagar',        icon: 'power-outline',   label: 'Apagar' },
  { action: 'subir_volumen', icon: 'volume-high',     label: 'Vol +' },
  { action: 'bajar_volumen', icon: 'volume-low',      label: 'Vol -' },
  { action: 'mute',          icon: 'volume-mute',     label: 'Mute' },
  { action: 'set_volumen',   icon: 'options-outline', label: 'Volumen', payloadType: 'volumen' },
];

const MEDIA_ACCIONES: ActionDef[] = [
  { action: 'encender',      icon: 'play',            label: 'Play' },
  { action: 'apagar',        icon: 'pause',           label: 'Pausa' },
  { action: 'subir_volumen', icon: 'volume-high',     label: 'Vol +' },
  { action: 'bajar_volumen', icon: 'volume-low',      label: 'Vol -' },
  { action: 'mute',          icon: 'volume-mute',     label: 'Mute' },
  { action: 'set_volumen',   icon: 'options-outline', label: 'Volumen', payloadType: 'volumen' },
];

const LUZ_ACCIONES: ActionDef[] = [
  { action: 'encender',          icon: 'sunny',               label: 'Encender' },
  { action: 'apagar',            icon: 'moon-outline',        label: 'Apagar' },
  { action: 'brillo',            icon: 'contrast',            label: 'Brillo',      payloadType: 'brightness' },
  { action: 'temperatura_color', icon: 'thermometer-outline', label: 'Temperatura', payloadType: 'color_temp' },
];

const LUZ_TUYA_ACCIONES: ActionDef[] = [
  ...LUZ_ACCIONES,
  { action: 'color_rgb', icon: 'color-palette-outline', label: 'Color', payloadType: 'color' },
];

// ── Type → actions map ────────────────────────────────────────────────────────

const ACTIONS_MAP: Record<string, ActionDef[]> = {
  SmartTV:      TV_ACCIONES,
  Luz:          LUZ_ACCIONES,       // Tuya variant resolved at runtime via getActionsForType
  Enchufe:      ON_OFF,
  IoT:          ON_OFF,
  Altavoz:      SPEAKER_ACCIONES,
  // Home Assistant domains
  light:        LUZ_ACCIONES,
  switch:       ON_OFF,
  climate:      ON_OFF,
  media_player: MEDIA_ACCIONES,
};

export const DEFAULT_ACCIONES: ActionDef[] = ON_OFF;

/**
 * Returns the action list for a given device type.
 * Pass isTuya=true for Luz devices that support color_rgb.
 */
export function getActionsForType(type: string, isTuya = false): ActionDef[] {
  if (isTuya && TUYA_BULB_TYPES.has(type)) {
    return LUZ_TUYA_ACCIONES;
  }
  return ACTIONS_MAP[type] ?? DEFAULT_ACCIONES;
}

/** True if the action requires the user to supply a payload value. */
export function actionNeedsPayload(action: ActionDef): boolean {
  return action.payloadType !== undefined;
}
