import { render, screen } from '@testing-library/react-native';
import { View } from 'react-native';
import { MessageBubble } from '@/components/chat/message-bubble';

const mensajeBot = {
  id: 'm1',
  from: 'bot',
  text: 'Encendiendo la luz del salón',
  timestamp: new Date('2026-04-12T10:30:00.000Z'),
};

describe('<MessageBubble />', () => {
  it('pinta el cuerpo del mensaje recibido', () => {
    render(<MessageBubble item={mensajeBot} />);
    expect(screen.getByText('Encendiendo la luz del salón')).toBeTruthy();
  });

  it('los mensajes del bot añaden avatar y los del usuario lo omiten', () => {
    const { UNSAFE_root: arbolBot } = render(<MessageBubble item={mensajeBot} />);
    const { UNSAFE_root: arbolUsuario } = render(
      <MessageBubble item={{ ...mensajeBot, from: 'me', text: 'enciende la luz del salón' }} />,
    );
    expect(arbolBot.findAllByType(View).length).toBeGreaterThan(
      arbolUsuario.findAllByType(View).length,
    );
  });
});
