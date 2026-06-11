import { render, screen } from '@testing-library/react-native';

jest.mock('@/utils/device-icons', () => ({
  deviceIcon: (type: string) => `icon-${type}`,
}));

import { BotDeviceList } from '@/components/chat/bot-device-list';

const cuandoFueEnviado = new Date('2026-04-12T10:30:00.000Z');

describe('<BotDeviceList />', () => {
  it('lista los dispositivos vinculados y ajusta el contador en plural', () => {
    render(
      <BotDeviceList
        dispositivos={[
          { id: 'd1', name: 'Luz Salón',      type: 'Luz',     is_online: true  },
          { id: 'd2', name: 'TV Salón',       type: 'SmartTV', is_online: false },
          { id: 'd3', name: 'Enchufe Cocina', type: 'Enchufe', is_online: true  },
        ]}
        total={3}
        timestamp={cuandoFueEnviado}
      />,
    );
    expect(screen.getByText('3 dispositivos vinculados')).toBeTruthy();
    expect(screen.getByText('Luz Salón')).toBeTruthy();
    expect(screen.getByText('TV Salón')).toBeTruthy();
    expect(screen.getByText('Enchufe Cocina')).toBeTruthy();
  });

  it('avisa al usuario cuando no tiene dispositivos vinculados', () => {
    render(<BotDeviceList dispositivos={[]} total={0} timestamp={cuandoFueEnviado} />);
    expect(screen.getByText('No tienes dispositivos vinculados.')).toBeTruthy();
  });
});
