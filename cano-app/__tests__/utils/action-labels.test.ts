import { labelForAction } from '@/utils/action-labels';

describe('labelForAction', () => {
  it('traduce las acciones del catálogo al texto que ve el usuario', () => {
    expect(labelForAction('temperatura_color')).toBe('Cambiar temperatura');
  });

  it('devuelve la acción tal cual si no está en el catálogo', () => {
    expect(labelForAction('encender_neveras')).toBe('encender_neveras');
  });
});
