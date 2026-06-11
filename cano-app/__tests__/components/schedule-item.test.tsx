import { fireEvent, render, screen } from '@testing-library/react-native';
import { Switch } from 'react-native';
import { ScheduleItem } from '@/components/schedules/schedule-item';

function tareaProgramada(over: any = {}) {
  return {
    id: 'sched-luz-noche',
    user_id: 'aleecr04',
    name: 'Apagar luces a medianoche',
    action: 'apagar',
    payload: {},
    cron_expr: '0 23 * * *',
    next_run_at: '2026-04-12T23:00:00.000Z',
    is_active: true,
    devices: { name: 'Luz Salón' },
    last_command: null,
    ...over,
  };
}

describe('<ScheduleItem />', () => {
  it('muestra nombre, dispositivo y horario derivado del cron', () => {
    render(
      <ScheduleItem schedule={tareaProgramada()} currentUserId="aleecr04"
        onToggle={jest.fn()} onDelete={jest.fn()} />,
    );
    expect(screen.getByText('Apagar luces a medianoche')).toBeTruthy();
    expect(screen.getByText(/Luz Salón/)).toBeTruthy();
    expect(screen.getByText(/Cada día a las 23:00/)).toBeTruthy();
  });

  it('marca como Completada las tareas puntuales que ya se ejecutaron', () => {
    render(
      <ScheduleItem schedule={tareaProgramada({ cron_expr: null, is_active: false })}
        currentUserId="aleecr04" onToggle={jest.fn()} onDelete={jest.fn()} />,
    );
    expect(screen.getByText('Completada')).toBeTruthy();
  });

  it('etiqueta con el nombre del autor las tareas creadas por otro miembro', () => {
    render(
      <ScheduleItem schedule={tareaProgramada({ user_id: 'maria' })} currentUserId="aleecr04"
        currentUserRole="member" creatorUsername="maria"
        onToggle={jest.fn()} onDelete={jest.fn()} />,
    );
    expect(screen.getByText('maria')).toBeTruthy();
  });

  it('dispara onToggle al cambiar el interruptor de activación', () => {
    const onToggle = jest.fn();
    render(
      <ScheduleItem schedule={tareaProgramada()} currentUserId="aleecr04"
        onToggle={onToggle} onDelete={jest.fn()} />,
    );
    fireEvent(screen.UNSAFE_getByType(Switch), 'valueChange', false);
    expect(onToggle).toHaveBeenCalledWith('sched-luz-noche', false);
  });

  it('etiqueta el cron como "Días laborables" cuando el dow es 1-5', () => {
    render(
      <ScheduleItem schedule={tareaProgramada({ cron_expr: '0 8 * * 1-5' })}
        currentUserId="aleecr04" onToggle={jest.fn()} onDelete={jest.fn()} />,
    );
    expect(screen.getByText(/Días laborables/)).toBeTruthy();
  });

  it('etiqueta el cron como "Fines de semana" cuando el dow es 0,6', () => {
    render(
      <ScheduleItem schedule={tareaProgramada({ cron_expr: '0 9 * * 0,6' })}
        currentUserId="aleecr04" onToggle={jest.fn()} onDelete={jest.fn()} />,
    );
    expect(screen.getByText(/Fines de semana/)).toBeTruthy();
  });
});
