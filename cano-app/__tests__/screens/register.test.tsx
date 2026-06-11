import { fireEvent, render, screen, act } from '@testing-library/react-native';
import { TextInput } from 'react-native';

const mockSignIn = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ back: jest.fn(), push: jest.fn(), replace: jest.fn() }),
}));
jest.mock('@/components/auth/auth-header', () => ({ AuthHeader: () => null }));
jest.mock('../../api/supabase', () => ({
  supabase: { auth: { signInWithPassword: (...a: any[]) => mockSignIn(...a) } },
}));
jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: { removeItem: jest.fn() },
}));

(globalThis as any).fetch = jest.fn();

import RegisterScreen from '@/app/register';

function rellenarFormulario(over: Partial<Record<'first'|'last'|'user'|'email'|'pass'|'confirm', string>> = {}) {
  const valores = {
    first:   'Pepe',
    last:    'Reina',
    user:    'aleecr04',
    email:   'aleecr04@cano4.dev',
    pass:    'CanoBot2026!',
    confirm: 'CanoBot2026!',
    ...over,
  };
  const inputs = screen.UNSAFE_getAllByType(TextInput);
  fireEvent.changeText(inputs[0], valores.first);
  fireEvent.changeText(inputs[1], valores.last);
  fireEvent.changeText(inputs[2], valores.user);
  fireEvent.changeText(inputs[3], valores.email);
  fireEvent.changeText(inputs[4], valores.pass);
  fireEvent.changeText(inputs[5], valores.confirm);
}

beforeEach(() => {
  mockSignIn.mockReset();
  ((globalThis as any).fetch as jest.Mock).mockReset();
});

describe('<RegisterScreen />', () => {
  it('rechaza el registro cuando las contraseñas no coinciden', () => {
    render(<RegisterScreen />);
    rellenarFormulario({ confirm: 'OtraPass1' });
    fireEvent.press(screen.getByText('Crear cuenta'));
    expect(screen.getByText('Las contraseñas no coinciden')).toBeTruthy();
  });

  it('llama a /users/signup con el cuerpo del formulario cuando es válido', async () => {
    ((globalThis as any).fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({}) });
    mockSignIn.mockResolvedValue({ error: null });
    render(<RegisterScreen />);
    rellenarFormulario();
    await act(async () => {
      fireEvent.press(screen.getByText('Crear cuenta'));
    });
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/users/signup'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('abre el modal con las credenciales XMPP cuando el backend las devuelve', async () => {
    ((globalThis as any).fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        xmpp_jid:      'aleecr04@xmpp.aleecr.es',
        xmpp_password: 'wQ7-Eb3rT2zN',
      }),
    });
    render(<RegisterScreen />);
    rellenarFormulario();
    await act(async () => {
      fireEvent.press(screen.getByText('Crear cuenta'));
    });
    expect(screen.getByText('Tus credenciales XMPP')).toBeTruthy();
    expect(screen.getByText('aleecr04@xmpp.aleecr.es')).toBeTruthy();
    expect(screen.getByText('wQ7-Eb3rT2zN')).toBeTruthy();
  });
});
