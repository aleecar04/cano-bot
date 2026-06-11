import { fireEvent, render, screen } from '@testing-library/react-native';
import { TouchableOpacity } from 'react-native';
import { LinkDeviceModal } from '@/components/devices/link-device-modal';

const dispositivoEscaneado = {
  ip: '192.0.2.42',
  mac: 'AA:BB:CC:DD:EE:01',
  hostname: 'salon-lamp',
  tipo: 'Luz',
};

describe('<LinkDeviceModal />', () => {
  it('pide credenciales Tuya para dispositivos compatibles', () => {
    render(
      <LinkDeviceModal
        visible
        device={{ ...dispositivoEscaneado, tipo: 'Luz' }}
        rooms={[]}
        linking={false}
        onClose={jest.fn()}
        onConfirm={jest.fn()}
      />,
    );
    expect(screen.getByText('Credenciales Tuya')).toBeTruthy();
  });

  it('omite el bloque Tuya para dispositivos como SmartTV', () => {
    render(
      <LinkDeviceModal
        visible
        device={{ ...dispositivoEscaneado, tipo: 'SmartTV' }}
        rooms={[]}
        linking={false}
        onClose={jest.fn()}
        onConfirm={jest.fn()}
      />,
    );
    expect(screen.queryByText('Credenciales Tuya')).toBeNull();
  });

  it('al confirmar envía dev_id y local_key dentro de la config Tuya', () => {
    const onConfirm = jest.fn();
    render(
      <LinkDeviceModal
        visible
        device={dispositivoEscaneado}
        rooms={[]}
        linking={false}
        onClose={jest.fn()}
        onConfirm={onConfirm}
      />,
    );
    fireEvent.changeText(screen.getByPlaceholderText('bf3a...'), 'bf12345abc');
    fireEvent.changeText(screen.getByPlaceholderText('a1b2c3d4e5f6...'), 'localkey-abcd');
    fireEvent.press(screen.UNSAFE_getAllByType(TouchableOpacity).at(-1)!);
    expect(onConfirm).toHaveBeenCalledWith(expect.objectContaining({
      ip: '192.0.2.42',
      config: expect.objectContaining({ dev_id: 'bf12345abc', local_key: 'localkey-abcd' }),
    }));
  });
});
