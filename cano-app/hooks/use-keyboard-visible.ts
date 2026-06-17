import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

/**
 * Web (PWA) only: indica si el teclado virtual está abierto, comparando la altura
 * del viewport visible con la del layout. Sirve para ocultar el footer/tab-bar
 * mientras se escribe, de modo que el teclado lo tape sin que "salte" hacia arriba.
 * En nativo siempre devuelve false (RN ya gestiona el teclado).
 */
export function useKeyboardVisible(): boolean {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined' || !window.visualViewport) {
      return;
    }
    const vv = window.visualViewport;
    const update = () => {
      // Umbral generoso para no confundir barras del navegador con el teclado.
      setVisible(window.innerHeight - vv.height > 150);
    };
    update();
    vv.addEventListener('resize', update);
    vv.addEventListener('scroll', update);
    return () => {
      vv.removeEventListener('resize', update);
      vv.removeEventListener('scroll', update);
    };
  }, []);

  return visible;
}
