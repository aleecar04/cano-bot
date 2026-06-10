export const ACTION_LABELS: Record<string, string> = {
  encender:          'Encender',
  apagar:            'Apagar',
  brillo:            'Cambiar brillo',
  temperatura_color: 'Cambiar temperatura',
  color_rgb:         'Cambiar color',
  subir_volumen:     'Subir volumen',
  bajar_volumen:     'Bajar volumen',
  mute:              'Silenciar',
  set_volumen:       'Ajustar volumen',
  abrir_app:         'Abrir aplicación',
  scan:              'Escanear red',
  list_devices:      'Listar dispositivos',
  ayuda:             'Ver ayuda',
  acciones:          'Ver acciones',
  saludo:            'Saludo',
};

export function labelForAction(action: string): string {
  return ACTION_LABELS[action] ?? action;
}
