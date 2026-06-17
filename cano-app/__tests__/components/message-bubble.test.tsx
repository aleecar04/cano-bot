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

    // Las respuestas del bot con viñetas se agrupan en cajitas por sección.
    const texto = [
      '• acción suelta',           // viñeta sin sección → intro
      'Tienes 2 dispositivos:',    // ':' pero la siguiente no es viñeta → intro
      'Luz:',                      // ':' y la siguiente es viñeta → título de sección
      '  • encender',
      '  • apagar',
      'Fin',                       // línea normal → intro
    ].join('\n');
    const { getByText } = render(<MessageBubble item={{ ...mensajeBot, text: texto }} />);
    expect(getByText('Luz')).toBeTruthy();         // título de la cajita (sin ':')
    expect(getByText('• encender')).toBeTruthy();  // viñeta dentro de la cajita
    expect(getByText('• apagar')).toBeTruthy();
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
