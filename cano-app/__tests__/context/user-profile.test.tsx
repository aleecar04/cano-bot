import { act, render } from '@testing-library/react-native';
import { Text } from 'react-native';

jest.mock('@/api/users', () => ({
  getUserProfile: jest.fn(),
}));
import { getUserProfile } from '@/api/users';
import { UserProfileProvider, useUserProfile } from '@/context/user-profile';

type Captured = { api: ReturnType<typeof useUserProfile> };

function Probe({ captured }: Readonly<{ captured: Captured }>) {
  captured.api = useUserProfile();
  return <Text>{captured.api.profile?.username ?? 'sin sesión activa'}</Text>;
}

function montarConSonda() {
  const captured: Captured = { api: null as any };
  render(
    <UserProfileProvider>
      <Probe captured={captured} />
    </UserProfileProvider>,
  );
  return captured;
}

describe('UserProfileContext', () => {
  beforeEach(() => (getUserProfile as jest.Mock).mockReset());

  it('loadProfile actualiza el perfil con los datos del backend', async () => {
    (getUserProfile as jest.Mock).mockResolvedValue({ username: 'aleecr04' });
    const captured = montarConSonda();
    await act(async () => { await captured.api.loadProfile(); });
    expect(captured.api.profile).toEqual({ username: 'aleecr04' });
  });

  it('loadProfile deja el perfil en blanco si la API responde con error', async () => {
    (getUserProfile as jest.Mock).mockRejectedValue(new Error('500'));
    const captured = montarConSonda();
    await act(async () => { await captured.api.loadProfile(); });
    expect(captured.api.profile).toBeNull();
  });

  it('clearProfile borra el perfil cargado al cerrar la sesión', async () => {
    (getUserProfile as jest.Mock).mockResolvedValue({ username: 'aleecr04' });
    const captured = montarConSonda();
    await act(async () => { await captured.api.loadProfile(); });
    act(() => { captured.api.clearProfile(); });
    expect(captured.api.profile).toBeNull();
  });
});
