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
        {/* Bloquea el scroll del documento: en iOS Safari, al enfocar un input
            el navegador hacía scroll de TODA la página (y el footer) hacia arriba.
            Anclando el body, el teclado se superpone y la pantalla no se mueve.
            El scroll vive en los contenedores internos (ScrollView/listas). */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              html, body { height: 100%; overflow: hidden; overscroll-behavior: none; }
              body { position: fixed; inset: 0; width: 100%; }
              #root { height: 100%; display: flex; flex-direction: column; }
            `,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
