import { ScrollViewStyleReset } from 'expo-router/html';
import { type PropsWithChildren } from 'react';

export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="es">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no, viewport-fit=cover, interactive-widget=overlays-content" />
        <title>Cano-Bot</title>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <meta name="theme-color" content="#3B82F6" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="Cano-Bot" />
        <ScrollViewStyleReset />
        {/* iOS Safari mueve el viewport visual (pan) al abrir el teclado y arrastra
            toda la pantalla y el footer hacia arriba. El CSS no lo evita: hay que
            pegar el body a la zona visible con la visualViewport API. */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              html, body { overflow: hidden; overscroll-behavior: none; }
              body { position: fixed; top: 0; left: 0; width: 100%; height: 100%; }
              #root { height: 100%; display: flex; flex-direction: column; }
            `,
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function () {
                if (typeof window === 'undefined' || !window.visualViewport) return;
                var vv = window.visualViewport;
                var raf = null;
                function apply() {
                  raf = null;
                  var b = document.body;
                  if (!b) return;
                  // Cancelamos el desplazamiento (offsetTop) que iOS aplica al abrir
                  // el teclado: empujamos el body fijo hacia abajo lo mismo que el
                  // navegador lo subió, así la pantalla y el footer NO se mueven.
                  // No encogemos la altura: el footer se queda en su sitio (el
                  // teclado simplemente lo tapa).
                  b.style.top = vv.offsetTop + 'px';
                  // Evita que iOS deje la ventana scrolleada tras cerrar el teclado.
                  if (vv.offsetTop === 0) window.scrollTo(0, 0);
                }
                function schedule() { if (raf == null) raf = requestAnimationFrame(apply); }
                vv.addEventListener('resize', schedule);
                vv.addEventListener('scroll', schedule);
                window.addEventListener('orientationchange', schedule);
                apply();
              })();
            `,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
