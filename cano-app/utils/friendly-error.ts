export function friendlyError(err: unknown): string {
  const msg = String(err).toLowerCase();

  if (
    msg.includes('network request failed') ||
    msg.includes('failed to fetch') ||
    msg.includes('econnrefused') ||
    msg.includes('enotfound') ||
    msg.includes('timeout') ||
    msg.includes('no disponible') ||
    msg.includes('servicio')
  ) {
    return 'Sin conexión. Comprueba que estás en la misma red y vuelve a intentarlo.';
  }

  if (msg.includes('401') || msg.includes('unauthorized') || msg.includes('credenciales')) {
    return 'Tu sesión ha expirado. Vuelve a iniciar sesión.';
  }

  if (msg.includes('404') || msg.includes('not found') || msg.includes('no encontrad')) {
    return 'No se encontró el recurso solicitado. Puede que haya cambiado.';
  }

  if (msg.includes('500') || msg.includes('503') || msg.includes('server')) {
    return 'Algo ha fallado en el servidor. Inténtalo de nuevo en un momento.';
  }

  if (msg.includes('vincul') || msg.includes('device')) {
    return 'No se pudo añadir el dispositivo. Comprueba que está encendido y vuelve a intentarlo.';
  }

  return 'Algo ha fallado. Inténtalo de nuevo.';
}
