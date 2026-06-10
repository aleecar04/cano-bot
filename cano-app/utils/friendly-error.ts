export function friendlyError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  const msg = raw.toLowerCase();

  // ── Errores de red / conectividad ────────────────────────────────────────────
  if (
    msg.includes('network request failed') ||
    msg.includes('failed to fetch') ||
    msg.includes('econnrefused') ||
    msg.includes('enotfound') ||
    msg.includes('timeout') ||
    msg.includes('no disponible') ||
    msg.includes('sin conexión')
  ) {
    return 'Sin conexión. Comprueba que estás en la misma red y vuelve a intentarlo.';
  }

  // ── Autenticación ─────────────────────────────────────────────────────────────
  if (msg.includes('401') || msg.includes('unauthorized') || msg.includes('credenciales')) {
    return 'Tu sesión ha expirado. Vuelve a iniciar sesión.';
  }

  // ── Recurso no encontrado ─────────────────────────────────────────────────────
  if (msg.includes('404') || msg.includes('not found') || msg.includes('no encontrad')) {
    return 'No se encontró el recurso solicitado.';
  }

  // ── Error de servidor ─────────────────────────────────────────────────────────
  if (msg.includes('500') || msg.includes('503')) {
    return 'Algo ha fallado en el servidor. Inténtalo de nuevo en un momento.';
  }

 
  if (
    raw.length > 0 &&
    raw.length < 120 &&
    !raw.includes('at ') &&       // no es stack trace
    !raw.includes('undefined') &&
    !raw.includes('null') &&
    !raw.toLowerCase().includes('exception') &&
    !raw.toLowerCase().includes('traceback')
  ) {
    // Capitalizar primera letra si no lo está
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }

  // ── Fallback ──────────────────────────────────────────────────────────────────
  return 'Algo ha fallado. Inténtalo de nuevo.';
}
