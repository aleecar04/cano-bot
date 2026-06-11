import { fireEvent, render, screen, waitFor, act } from '@testing-library/react-native';
import { TextInput } from 'react-native';

const mockGetSession = jest.fn();
const mockUpdateUser = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn(), back: jest.fn() }),
}));
jest.mock('@/components/auth/auth-header', () => {
  const { Text } = jest.requireActual('react-native');
  return { AuthHeader: ({ title }: any) => <Text>{title}</Text> };
});
jest.mock('../../api/supabase', () => ({
  supabase: {
    auth: {
      getSession: (...a: any[]) => mockGetSession(...a),
      updateUser: (...a: any[]) => mockUpdateUser(...a),
      signOut:    jest.fn(),
    },
  },
}));

import ResetPasswordScreen from '@/app/reset-password';

beforeEach(() => {
  mockGetSession.mockReset();
  mockUpdateUser.mockReset();
});

describe('<ResetPasswordScreen />', () => {
  it('avisa de enlace inválido cuando el usuario llega sin sesión activa', async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    render(<ResetPasswordScreen />);
    await waitFor(() => expect(screen.getByText('Enlace inválido')).toBeTruthy(), { timeout: 10000 });
  }, 15000);

  it('rechaza el cambio si las dos contraseñas no coinciden', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'aleecr04' } } } });
    render(<ResetPasswordScreen />);
    await waitFor(() => screen.getByText('Cambiar contraseña'));
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'CanoBot2026!');
    fireEvent.changeText(inputs[1], 'CanoBot1999!');
    fireEvent.press(screen.getByText('Cambiar contraseña'));
    expect(screen.getByText('Las contraseñas no coinciden')).toBeTruthy();
  });

  it('llama a Supabase con la nueva contraseña cuando pasa las validaciones', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'aleecr04' } } } });
    mockUpdateUser.mockResolvedValue({ error: null });
    render(<ResetPasswordScreen />);
    await waitFor(() => screen.getByText('Cambiar contraseña'));
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'CanoBot2026!');
    fireEvent.changeText(inputs[1], 'CanoBot2026!');
    await act(async () => {
      fireEvent.press(screen.getByText('Cambiar contraseña'));
    });
    expect(mockUpdateUser).toHaveBeenCalledWith({ password: 'CanoBot2026!' });
  });

  it('rechaza una contraseña con menos de 8 caracteres', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'aleecr04' } } } });
    render(<ResetPasswordScreen />);
    await waitFor(() => screen.getByText('Cambiar contraseña'));
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'corta');
    fireEvent.changeText(inputs[1], 'corta');
    fireEvent.press(screen.getByText('Cambiar contraseña'));
    expect(screen.getByText('La contraseña debe tener al menos 8 caracteres')).toBeTruthy();
  });

  it('muestra el mensaje de error cuando Supabase rechaza el cambio', async () => {
    mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'aleecr04' } } } });
    mockUpdateUser.mockResolvedValue({ error: { message: 'New password should be different from the old password' } });
    render(<ResetPasswordScreen />);
    await waitFor(() => screen.getByText('Cambiar contraseña'));
    const inputs = screen.UNSAFE_getAllByType(TextInput);
    fireEvent.changeText(inputs[0], 'CanoBot2026!');
    fireEvent.changeText(inputs[1], 'CanoBot2026!');
    await act(async () => {
      fireEvent.press(screen.getByText('Cambiar contraseña'));
    });
    expect(screen.getByText(/different from the old password/)).toBeTruthy();
  });
});
