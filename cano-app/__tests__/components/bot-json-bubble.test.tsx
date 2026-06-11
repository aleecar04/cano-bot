import { render } from '@testing-library/react-native';

const mockScanResponse = jest.fn();
const mockDeviceList   = jest.fn();

jest.mock('@/components/chat/bot-scan-response', () => ({
  BotScanResponse: (props: any) => { mockScanResponse(props); return null; },
}));
jest.mock('@/components/chat/bot-device-list', () => ({
  BotDeviceList: (props: any) => { mockDeviceList(props); return null; },
}));

import { BotJsonBubble } from '@/components/chat/bot-json-bubble';

const cuandoFueEnviado = new Date('2026-04-12T10:30:00.000Z');

beforeEach(() => {
  mockScanResponse.mockReset();
  mockDeviceList.mockReset();
});

describe('<BotJsonBubble />', () => {
  it('despacha a BotScanResponse cuando el bot envía un escaneo de red', () => {
    render(
      <BotJsonBubble
        data={{
          tipo: 'scan_response',
          red: '192.0.2.0/24',
          ip_bot: '192.0.2.10',
          dispositivos: [{ ip: '192.0.2.42' }],
          total: 1,
        }}
        timestamp={cuandoFueEnviado}
      />,
    );
    expect(mockScanResponse).toHaveBeenCalled();
    expect(mockDeviceList).not.toHaveBeenCalled();
  });

  it('despacha a BotDeviceList cuando el bot envía el listado de dispositivos', () => {
    render(
      <BotJsonBubble
        data={{ tipo: 'device_list', dispositivos: [{ id: 'd1' }], total: 1 }}
        timestamp={cuandoFueEnviado}
      />,
    );
    expect(mockDeviceList).toHaveBeenCalled();
  });

  it('no muestra nada cuando el tipo del payload es desconocido', () => {
    const { toJSON } = render(
      <BotJsonBubble data={{ tipo: 'estadistica_diaria' }} timestamp={cuandoFueEnviado} />,
    );
    expect(toJSON()).toBeNull();
  });
});
