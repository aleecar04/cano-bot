import { fireEvent, render, screen, act } from '@testing-library/react-native';
import { AddRoomModal } from '@/components/casa/add-room-modal';

describe('<AddRoomModal />', () => {
  it('no llama a onAddRoom cuando el nombre de la habitación está vacío', () => {
    const onAddRoom = jest.fn();
    render(
      <AddRoomModal
        visible
        floorId="planta-baja"
        floorName="Planta Baja"
        onClose={jest.fn()}
        onAddRoom={onAddRoom}
      />,
    );
    fireEvent.press(screen.getByText('Añadir'));
    expect(onAddRoom).not.toHaveBeenCalled();
  });

  it('dispara onAddRoom con el nombre saneado cuando el usuario confirma', async () => {
    const onAddRoom = jest.fn().mockResolvedValue(undefined);
    render(
      <AddRoomModal
        visible
        floorId="planta-baja"
        floorName="Planta Baja"
        onClose={jest.fn()}
        onAddRoom={onAddRoom}
      />,
    );
    fireEvent.changeText(screen.getByDisplayValue(''), '  Cocina  ');
    await act(async () => {
      fireEvent.press(screen.getByText('Añadir'));
    });
    expect(onAddRoom).toHaveBeenCalledWith('planta-baja', 'Cocina');
  });

  it('llama a onClose al pulsar Cancelar', () => {
    const onClose = jest.fn();
    render(
      <AddRoomModal
        visible
        floorId="planta-baja"
        floorName="Planta Baja"
        onClose={onClose}
        onAddRoom={jest.fn()}
      />,
    );
    fireEvent.press(screen.getByText('Cancelar'));
    expect(onClose).toHaveBeenCalled();
  });
});
