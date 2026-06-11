import { fireEvent, render, screen } from '@testing-library/react-native';
import { ActivityIndicator } from 'react-native';
import { Button } from '@/components/ui/button';

describe('<Button />', () => {
  it('dispara onPress cuando el usuario lo pulsa', () => {
    const onPress = jest.fn();
    render(<Button label="Iniciar sesión" onPress={onPress} />);
    fireEvent.press(screen.getByText('Iniciar sesión'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('reemplaza el label por un spinner mientras la acción está en curso', () => {
    const { UNSAFE_getByType } = render(
      <Button label="Iniciar sesión" onPress={jest.fn()} loading />,
    );
    expect(UNSAFE_getByType(ActivityIndicator)).toBeTruthy();
    expect(screen.queryByText('Iniciar sesión')).toBeNull();
  });
});
