import { render, screen } from '@testing-library/react-native';
import { ErrorMessage } from '@/components/ui/error-message';

describe('<ErrorMessage />', () => {
  it('queda invisible mientras no haya mensaje', () => {
    const { toJSON } = render(<ErrorMessage message={null} />);
    expect(toJSON()).toBeNull();
  });

  it('muestra el mensaje recibido por prop', () => {
    render(<ErrorMessage message="Usuario o contraseña incorrectos" />);
    expect(screen.getByText('Usuario o contraseña incorrectos')).toBeTruthy();
  });
});
