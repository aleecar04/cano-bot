import { fireEvent, render, screen } from '@testing-library/react-native';
import { TouchableOpacity } from 'react-native';

jest.mock('@/api/devices', () => ({
  sendCommand:    jest.fn(),
  waitForCommand: jest.fn(),
  getDevice:      jest.fn(),
  refreshDevice:  jest.fn(),
}));
jest.mock('@/components/devices/device-edit-modal', () => ({
  DeviceEditModal: () => null,
}));
jest.mock('@/utils/device-icons', () => ({
  deviceIcon:  () => 'bulb',
  deviceColor: () => '#3B82F6',
}));

import { LinkedDeviceItem } from '@/components/devices/linked-device-item';

function dispositivoVinculado(over: Partial<React.ComponentProps<typeof LinkedDeviceItem>['device']> = {}) {
  return {
    id: 'd1',
    name: 'Luz Salón',
    type: 'Luz',
    ip: '192.0.2.42',
    mac: null,
    is_online: true,
    state: { power: 'off' },
    ...over,
  };
}

describe('<LinkedDeviceItem />', () => {
  it('muestra los datos básicos del dispositivo y sus badges de estado', () => {
    render(
      <LinkedDeviceItem device={dispositivoVinculado()} onUnlink={jest.fn()} />,
    );
    expect(screen.getByText('Luz Salón')).toBeTruthy();
    expect(screen.getByText('Luz · 192.0.2.42')).toBeTruthy();
    expect(screen.getByText('Disponible')).toBeTruthy();
    expect(screen.getByText('Apagado')).toBeTruthy();
  });

  it('refleja el estado offline + encendido cuando los datos del polling lo indican', () => {
    render(
      <LinkedDeviceItem
        device={dispositivoVinculado({ is_online: false, state: { power: 'on' } })}
        onUnlink={jest.fn()}
      />,
    );
    expect(screen.getByText('No disponible')).toBeTruthy();
    expect(screen.getByText('Encendido')).toBeTruthy();
  });

  it('dispara onUnlink con el dispositivo seleccionado al pulsar la papelera', () => {
    const onUnlink = jest.fn();
    render(<LinkedDeviceItem device={dispositivoVinculado()} onUnlink={onUnlink} />);
    fireEvent.press(screen.UNSAFE_getAllByType(TouchableOpacity).at(-1)!);
    expect(onUnlink).toHaveBeenCalledWith('d1', 'Luz Salón');
  });
});
