import { fireEvent, render, screen } from '@testing-library/react-native';
import { ConversationItem } from '@/components/chat/conversation-item';

const conversacion = {
  id: 'conv-2026-04-12',
  title: 'Apagar TV antes de dormir',
  updated_at: '2026-04-12T22:30:00.000Z',
};

describe('<ConversationItem />', () => {
  it('muestra el título y dispara onPress con el id al seleccionar la conversación', () => {
    const onPress = jest.fn();
    render(<ConversationItem item={conversacion} onPress={onPress} />);
    fireEvent.press(screen.getByText('Apagar TV antes de dormir'));
    expect(onPress).toHaveBeenCalledWith('conv-2026-04-12');
  });
});
