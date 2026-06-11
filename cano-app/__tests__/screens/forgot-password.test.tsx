import { fireEvent, render, screen, act } from '@testing-library/react-native';
import { Alert } from 'react-native';

const mockReset = jest.fn();
const mockAlert = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ back: jest.fn(), push: jest.fn(), replace: jest.fn() }),
}));
jest.mock('@/components/auth/auth-header', () => ({ AuthHeader: () => null }));
jest.mock('../../api/supabase', () => ({
  supabase: { auth: { resetPasswordForEmail: (...a: any[]) => mockReset(...a) } },
}));
jest.spyOn(Alert, 'alert').mockImplementation((...args: any[]) => mockAlert(...args));

import ForgotPasswordScreen from '@/app/forgot-password';

beforeEach(() => {
  mockReset.mockReset();
  mockAlert.mockReset();
});

describe('<ForgotPasswordScreen />', () => {
  it('no llama a Supabase si el usuario no ha introducido un email', () => {
    render(<ForgotPasswordScreen />);
    fireEvent.press(screen.getByText('Enviar enlace'));
    expect(screen.getByText('Introduce tu email')).toBeTruthy();
    expect(mockReset).not.toHaveBeenCalled();
  });

  it('envía el email saneado a Supabase para que mande el enlace de recuperación', async () => {
    mockReset.mockResolvedValue({ error: null });
    render(<ForgotPasswordScreen />);
    fireEvent.changeText(screen.getByDisplayValue(''), '  ALEECR04@cano4.dev  ');
    await act(async () => {
      fireEvent.press(screen.getByText('Enviar enlace'));
    });
    expect(mockReset).toHaveBeenCalledWith(
      'aleecr04@cano4.dev',
      expect.objectContaining({ redirectTo: expect.any(String) }),
    );
  });

  it('muestra el mensaje cuando Supabase devuelve error', async () => {
    mockReset.mockResolvedValue({ error: { message: 'Rate limit exceeded' } });
    render(<ForgotPasswordScreen />);
    fireEvent.changeText(screen.getByDisplayValue(''), 'anabel@cano-app.com');
    await act(async () => {
      fireEvent.press(screen.getByText('Enviar enlace'));
    });
    expect(screen.getByText('Rate limit exceeded')).toBeTruthy();
  });
});
