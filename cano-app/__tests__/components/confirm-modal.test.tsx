import { fireEvent, render, screen } from '@testing-library/react-native';
import { ConfirmModal } from '@/components/ui/confirm-modal';

describe('<ConfirmModal />', () => {
  it('renderiza título, mensaje y los labels por defecto del par de botones', () => {
    render(
      <ConfirmModal
        visible
        title="Eliminar Luz Salón"
        message="Se perderán las acciones favoritas asociadas"
        onConfirm={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(screen.getByText('Eliminar Luz Salón')).toBeTruthy();
    expect(screen.getByText('Se perderán las acciones favoritas asociadas')).toBeTruthy();
    expect(screen.getByText('Confirmar')).toBeTruthy();
    expect(screen.getByText('Cancelar')).toBeTruthy();
  });

  it('dispara los callbacks correctos al pulsar cada botón', () => {
    const onConfirm = jest.fn();
    const onCancel = jest.fn();
    render(
      <ConfirmModal
        visible
        title="Eliminar Luz Salón"
        onConfirm={onConfirm}
        onCancel={onCancel}
        confirmLabel="Eliminar"
      />,
    );
    fireEvent.press(screen.getByText('Eliminar'));
    fireEvent.press(screen.getByText('Cancelar'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
