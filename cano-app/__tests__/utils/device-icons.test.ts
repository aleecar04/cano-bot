import { deviceIcon, deviceColor } from '@/utils/device-icons';

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
  });

  it('usa un color neutro para tipos fuera del catálogo', () => {
    expect(deviceColor('Microondas')).toBe('#94a3b8');
  });
});
