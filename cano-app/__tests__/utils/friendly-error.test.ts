import { friendlyError } from '@/utils/friendly-error';

describe('friendlyError', () => {
  it('convierte un fallo de red en un aviso de conexión', () => {
    expect(friendlyError(new Error('Network request failed'))).toMatch(/sin conexi[oó]n/i);
  });

  it('convierte un 401 en un aviso de sesión caducada', () => {
    expect(friendlyError(new Error('HTTP 401 Unauthorized'))).toMatch(/sesi[oó]n ha expirado/i);
  });

  it('cae al mensaje genérico ante stack traces o errores inservibles', () => {
    expect(friendlyError(new Error('Exception at services/foo.js:12'))).toMatch(/algo ha fallado/i);
  });

  it('traduce 404 a recurso no encontrado', () => {
    expect(friendlyError(new Error('HTTP 404 Not Found'))).toMatch(/no se encontró/i);
  });

  it('traduce 500 a fallo del servidor', () => {
    expect(friendlyError(new Error('HTTP 500 Internal Server Error'))).toMatch(/servidor/i);
  });

  it('capitaliza un mensaje corto y útil', () => {
    expect(friendlyError(new Error('el código ha caducado'))).toBe('El código ha caducado');
  });
});
