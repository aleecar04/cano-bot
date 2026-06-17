import { fireEvent, render, screen } from '@testing-library/react-native';

jest.mock('@/utils/device-icons', () => ({
  deviceIcon:  () => 'bulb',
  deviceColor: () => '#3B82F6',
  deviceTypeLabel: (t: string) => t,
}));

import { AddFavoriteModal } from '@/components/ui/add-favorite-modal';

const luzSalon = {
  id: 'd1', name: 'Luz Salón', type: 'Luz', driver: 'tuya',
  is_online: true, state: {}, ip: '192.0.2.42', mac: 'AA:BB:CC:DD:EE:01',
  config: {}, room_id: null, location: null,
  last_seen_at: null, registered_at: null, updated_at: null,
};

describe('<AddFavoriteModal />', () => {
  it('avanza del selector de dispositivos al selector de acciones', () => {
    render(
      <AddFavoriteModal
        visible
        devices={[luzSalon]}
        saving={false}
        onClose={jest.fn()}
        onSelectAction={jest.fn()}
      />,
    );
    fireEvent.press(screen.getByText('Luz Salón'));
    expect(screen.getByText('Encender')).toBeTruthy();
  });
});
