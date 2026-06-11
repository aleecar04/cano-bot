import { fireEvent, render, screen, act } from '@testing-library/react-native';
import { TextInput } from 'react-native';

const mockSignIn = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn(), back: jest.fn() }),
}));
jest.mock('@/components/auth/auth-header', () => ({ AuthHeader: () => null }));
jest.mock('../../api/supabase', () => ({
  supabase: { auth: { signInWithPassword: (...args: any[]) => mockSignIn(...args) } },
}));

(globalThis as any).fetch = jest.fn();

import LoginScreen from '@/app/login';

beforeEach(() => {
  mockSignIn.mockReset();
  ((globalThis as any).fetch as jest.Mock).mockReset();
});

describe('<LoginScreen />', () => {
  it('no envía la petición si los campos están vacíos', () => {
    render(<LoginScreen />);
    fireEvent.press(screen.getByText('Iniciar sesión'));
    expect(screen.getByText('Rellena todos los campos')).toBeTruthy();
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it('llama a Supabase con email y password cuando las credenciales son válidas', async () => {
    mockSignIn.mockResolvedValue({ error: null });
    render(<LoginScreen />);
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'aleecr04@cano4.dev');
    fireEvent.changeText(inputs[1], 'CanoBot2026!');
    await act(async () => {
      fireEvent.press(screen.getByText('Iniciar sesión'));
    });
    expect(mockSignIn).toHaveBeenCalledWith({
      email: 'aleecr04@cano4.dev',
      password: 'CanoBot2026!',
    });
  });

  it('muestra el aviso de credenciales incorrectas cuando Supabase las rechaza', async () => {
    mockSignIn.mockResolvedValue({ error: { message: 'Invalid login credentials' } });
    render(<LoginScreen />);
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'aleecr04@cano4.dev');
    fireEvent.changeText(inputs[1], 'mal-password');
    await act(async () => {
      fireEvent.press(screen.getByText('Iniciar sesión'));
    });
    expect(screen.getByText('Email, usuario o contraseña incorrectos')).toBeTruthy();
  });

  it('resuelve el email cuando se introduce un username', async () => {
    ((globalThis as any).fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ email: 'anabel@cano-app.com' }),
    });
    mockSignIn.mockResolvedValue({ error: null });
    render(<LoginScreen />);
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'anabel');
    fireEvent.changeText(inputs[1], 'CanoBot2026!');
    await act(async () => {
      fireEvent.press(screen.getByText('Iniciar sesión'));
    });
    expect(mockSignIn).toHaveBeenCalledWith({
      email: 'anabel@cano-app.com',
      password: 'CanoBot2026!',
    });
  });

  it('avisa cuando Supabase exige verificar el correo', async () => {
    mockSignIn.mockResolvedValue({ error: { message: 'Email not verified' } });
    render(<LoginScreen />);
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'anabel@cano-app.com');
    fireEvent.changeText(inputs[1], 'CanoBot2026!');
    await act(async () => {
      fireEvent.press(screen.getByText('Iniciar sesión'));
    });
    expect(screen.getByText('Debes verificar tu correo antes de iniciar sesión')).toBeTruthy();
  });
});
