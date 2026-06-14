import { fireEvent, render, screen } from '@testing-library/react-native';
import { TouchableOpacity } from 'react-native';

jest.mock('@/api/houses', () => ({
  roomSchedule:  jest.fn(),
  floorSchedule: jest.fn(),
}));

import { RoomGrid } from '@/components/casa/room-grid';

function makeRoom(over: any = {}) {
  return { id: 'r1', name: 'Salón', order: 0, ...over };
}

describe('<RoomGrid />', () => {
  it('muestra el nombre de la planta', () => {
    render(<RoomGrid floorId="f1" floorName="Planta baja" rooms={[]} />);
    expect(screen.getByText('Planta baja')).toBeTruthy();
  });

  it('muestra el mensaje de empty state cuando no hay habitaciones', () => {
    render(<RoomGrid floorId="f1" floorName="Planta baja" rooms={[]} />);
    expect(screen.getByText(/Sin habitaciones/)).toBeTruthy();
  });

  it('renderiza una entrada por cada habitación de la lista', () => {
    render(
      <RoomGrid
        floorId="f1"
        floorName="Planta baja"
        rooms={[makeRoom(), makeRoom({ id: 'r2', name: 'Cocina' })]}
      />,
    );
    expect(screen.getByText('Salón')).toBeTruthy();
    expect(screen.getByText('Cocina')).toBeTruthy();
    expect(screen.queryByText(/Sin habitaciones/)).toBeNull();
  });

  it('dispara onRoomPress al pulsar una habitación', () => {
    const onRoomPress = jest.fn();
    render(
      <RoomGrid
        floorId="f1"
        floorName="Planta baja"
        rooms={[makeRoom()]}
        onRoomPress={onRoomPress}
      />,
    );
    fireEvent.press(screen.getByText('Salón'));
    expect(onRoomPress).toHaveBeenCalledWith(expect.objectContaining({ id: 'r1' }));
  });

  it('dispara onDeleteFloor con id y nombre cuando se pulsa "Eliminar planta" en el menú', () => {
    const onDeleteFloor = jest.fn();
    render(
      <RoomGrid
        floorId="f1"
        floorName="Planta baja"
        rooms={[]}
        onDeleteFloor={onDeleteFloor}
      />,
    );
    const buttons = screen.UNSAFE_getAllByType(TouchableOpacity);
    fireEvent.press(buttons.at(-1)!);
    fireEvent.press(screen.getByText('Eliminar planta'));
    expect(onDeleteFloor).toHaveBeenCalledWith('f1', 'Planta baja');
  });
});
