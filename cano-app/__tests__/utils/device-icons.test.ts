import { deviceIcon, deviceColor, deviceTypeLabel } from '@/utils/device-icons';

describe('deviceIcon', () => {
  it('asigna el icono correcto a un dispositivo del catálogo', () => {
    expect(deviceIcon('Luz')).toBe('bulb-outline');
  });

  it('usa un icono genérico para tipos fuera del catálogo', () => {
    expect(deviceIcon('Microondas')).toBe('cube-outline');
  });
});

describe('deviceColor', () => {
  it('asigna el color correcto a un dispositivo del catálogo', () => {
    expect(deviceColor('SmartTV')).toBe('#8b5cf6');
    // Etiqueta legible del tipo: catálogo y dominios de Home Assistant.
    expect(deviceTypeLabel('SmartTV')).toBe('Smart TV');
    expect(deviceTypeLabel('light')).toBe('Luz');
    expect(deviceTypeLabel('switch')).toBe('Enchufe');
  });

  it('usa un color neutro para tipos fuera del catálogo', () => {
    expect(deviceColor('Microondas')).toBe('#94a3b8');
    // Tipo fuera del catálogo se devuelve tal cual; undefined → cadena vacía.
    expect(deviceTypeLabel('Microondas')).toBe('Microondas');
    expect(deviceTypeLabel(undefined)).toBe('');
  });
});
