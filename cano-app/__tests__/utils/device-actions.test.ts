import {
  actionNeedsPayload,
  getActionsForType,
  kelvinToHex,
  DEFAULT_ACCIONES,
} from '@/utils/device-actions';

describe('getActionsForType', () => {
  it('expone las acciones específicas del tipo de dispositivo', () => {
    expect(getActionsForType('Luz').some(a => a.action === 'brillo')).toBe(true);
    expect(getActionsForType('SmartTV').some(a => a.action === 'abrir_app')).toBe(true);
  });

  it('habilita color_rgb solo para luces Tuya', () => {
    expect(getActionsForType('Luz', true).some(a => a.action === 'color_rgb')).toBe(true);
    expect(getActionsForType('Luz', false).some(a => a.action === 'color_rgb')).toBe(false);
  });

  it('aplica el set por defecto a tipos no catalogados', () => {
    expect(getActionsForType('Microondas')).toBe(DEFAULT_ACCIONES);
  });
});

describe('actionNeedsPayload', () => {
  it('distingue las acciones que requieren un valor de las que no', () => {
    expect(actionNeedsPayload({ action: 'brillo', icon: 'x', label: 'X', payloadType: 'brightness' })).toBe(true);
    expect(actionNeedsPayload({ action: 'encender', icon: 'x', label: 'X' })).toBe(false);
  });
});

describe('kelvinToHex', () => {
  it('clampa los grados Kelvin a los límites soportados por las bombillas', () => {
    expect(kelvinToHex(1500)).toBe(kelvinToHex(2700));
    expect(kelvinToHex(9000)).toBe(kelvinToHex(6500));
  });
});
