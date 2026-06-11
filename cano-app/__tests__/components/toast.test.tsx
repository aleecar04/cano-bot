import { render, screen, act } from '@testing-library/react-native';
import { Toast } from '@/components/ui/toast';

describe('<Toast />', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('muestra el mensaje mientras está visible y desaparece tras el tiempo configurado', () => {
    const onHide = jest.fn();
    render(<Toast message="Casa creada correctamente" visible duration={1000} onHide={onHide} />);
    expect(screen.getByText('Casa creada correctamente')).toBeTruthy();
    act(() => { jest.advanceTimersByTime(2000); });
    expect(onHide).toHaveBeenCalled();
  });

  it('no renderiza nada mientras visible=false', () => {
    const { toJSON } = render(
      <Toast message="Token regenerado" visible={false} onHide={() => {}} />,
    );
    expect(toJSON()).toBeNull();
  });
});
