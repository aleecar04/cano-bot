# Cano-bot

Sistema domótico de control del hogar mediante un agente conversacional (chatbot) basado en el protocolo **XMPP**. Permite gestionar dispositivos IoT (luces, enchufes, televisores, etc.) tanto con controles desde una PWA como mediante mensajes en **lenguaje natural**, e integra **Home Assistant** para ampliar la compatibilidad.

El proyecto se compone de tres módulos:

- **`backend/`** — API REST (FastAPI) con la lógica de negocio y la persistencia en Supabase (PostgreSQL).
- **`errbot/`** — bot que se ejecuta en la red local del usuario y controla los dispositivos.
- **`cano-app/`** — aplicación web progresiva (PWA) en React Native / Expo.

## Instalación

### Requisitos

- Docker y Docker Compose.
- Para el bot, se recomienda un equipo **Linux** dentro de la red local del hogar (el descubrimiento de dispositivos usa el modo de red `host` de Docker).

### Desplegar el bot (sobre la instancia ya desplegada)

Se ofrece una instancia del sistema en <https://cano-bot.aleecr.es>. Basta con registrarse, crear una casa y copiar el *token de configuración del bot* que muestra la aplicación.

```bash
git clone https://github.com/aleecar04/cano-bot.git
cd cano-bot

cp errbot/.env.example errbot/.env
# Editar errbot/.env y fijar BOT_TOKEN=<token>

docker compose up -d --build bot
```

### (Opcional) Despliegue completo en local

Requiere completar el `.env` raíz con credenciales propias (Supabase, servidor XMPP, etc.) a partir de la plantilla `.env.example`.

```bash
cp .env.example .env        # rellenar con credenciales propias

supabase start
docker compose up -d --build

cd cano-app
npm install
npm start
```

## Autor

Alejandro Carmona Reina — Trabajo de Fin de Grado.
