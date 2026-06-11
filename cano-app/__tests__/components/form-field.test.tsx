import { fireEvent, render, screen } from '@testing-library/react-native';
import { FormField } from '@/components/ui/form-field';

describe('<FormField />', () => {
  it('propaga lo que escribe el usuario al callback onChangeText', () => {
    const onChangeText = jest.fn();
    render(<FormField label="Email" value="" onChangeText={onChangeText} />);
    fireEvent.changeText(screen.getByDisplayValue(''), 'aleecr04@cano4.dev');
    expect(onChangeText).toHaveBeenCalledWith('aleecr04@cano4.dev');
  });

  it('respeta el límite de caracteres configurado para el campo', () => {
    render(<FormField label="Usuario" value="" onChangeText={() => {}} maxLength={50} />);
    expect(screen.getByDisplayValue('').props.maxLength).toBe(50);
  });
});
