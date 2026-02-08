# Cano Bot - TFG Chatbot System

Sistema completo de chatbot con backend Errbot y aplicación móvil React Native.

## 📋 Descripción

Proyecto de TFG que implementa un sistema de chatbot completo, compuesto por:

- **Backend**: Bot basado en Errbot con almacenamiento en Supabase

- **Frontend**: Aplicación móvil multiplataforma con React Native y Expo

## 🏗️ Estructura del Proyecto

```
cano4/
├── venv/                 # Entorno virtual Python
├── config.py             # Configuración de Errbot
├── plugins/              # Plugins personalizados del bot
│   └── mibot/           # Plugin principal con integración Supabase
├── data/                 # Datos persistentes del bot
├── requirements.txt      # Dependencias Python
├── .env                  # Variables de entorno (credenciales)
└── cano-app/            # Aplicación móvil React Native
    ├── app/
    ├── components/
    ├── node_modules/
    └── package.json
```

## 🛠️ Tecnologías

### Backend

- **Python 3.12** - Lenguaje base
- **Errbot 6.2.0** - Framework para chatbots
- **Supabase 2.27.3** - Base de datos PostgreSQL en la nube
- **python-dotenv 1.2.1** - Gestión de variables de entorno
- **Pydantic 2.x** - Validación de datos

### Frontend (Aplicación Móvil)

- **React Native 0.81.5** - Framework multiplataforma
- **Expo ~54.0.33** - Herramientas de desarrollo
- **TypeScript ~5.9.2** - Tipado estático
- **Expo Router ~6.0.23** - Navegación basada en archivos
- **React Navigation 7.x** - Sistema de navegación
- **Redux Toolkit 2.11.2** - Gestión de estado
- **React Native Gifted Chat 3.3.2** - UI de chat
- **XMPP Client 0.14.0** - Protocolo de mensajería

### Base de Datos

- **PostgreSQL** (vía Supabase) - Base de datos relacional
- **Supabase Auth** - Autenticación de usuarios
- **Supabase Realtime** - Sincronización en tiempo real

## 📦 Instalación

### Prerrequisitos

- Python 3.12+
- Node.js 20.19.4+
- npm 9.2.0+
- Cuenta en Supabase

### Backend (Errbot)

```bash
# Clonar repositorio
git clone <tu-repo>
cd cano4

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase

# Ejecutar el bot
errbot
```

### Frontend (App Móvil)

```bash
# Ir a la carpeta de la app
cd cano-app

# Instalar dependencias
npm install

# Instalar Supabase
npm install @supabase/supabase-js

# Ejecutar en desarrollo
npm start

# Ejecutar en Android
npm run android

# Ejecutar en iOS
npm run ios
```

## ⚙️ Configuración

### 1. Supabase

1. Crear proyecto en [supabase.com](https://supabase.com)
2. Crear tabla `mensajes`:

```sql
   CREATE TABLE mensajes (
     id BIGSERIAL PRIMARY KEY,
     usuario TEXT NOT NULL,
     texto TEXT NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
```

3. Obtener credenciales en Project Settings → API

### 2. Variables de Entorno

Crear archivo `.env` en la raíz:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key-aqui
```

### 3. Configuración del Bot

Editar `config.py`:

- Cambiar `BOT_ADMINS` con tu usuario
- Verificar rutas de directorios

## 🚀 Uso

### Comandos del Bot

```
!help              # Muestra ayuda
!guardar <texto>   # Guarda mensaje en Supabase
!listar            # Muestra últimos mensajes
!plugin activate MiBot  # Activa el plugin principal
```

### App Móvil

1. Iniciar la app con `npm start`
2. Escanear QR con Expo Go (Android/iOS)
3. Conectar con el bot vía XMPP
4. Enviar/recibir mensajes en tiempo real

## 📱 Características de la App

- ✅ Chat en tiempo real con Gifted Chat
- ✅ Navegación con React Navigation + Expo Router
- ✅ Gestión de estado con Redux Toolkit
- ✅ Notificaciones push
- ✅ Integración con Supabase
- ✅ Protocolo XMPP para mensajería
- ✅ Soporte multiplataforma (iOS/Android/Web)

## 🧪 Testing

```bash
# Backend
cd cano4
source venv/bin/activate
pytest  # (si se añaden tests)

# Frontend
cd cano-app
npm run lint
```

## 📚 Documentación Adicional

- [Errbot Documentation](https://errbot.readthedocs.io/)
- [Supabase Docs](https://supabase.com/docs)
- [React Native Docs](https://reactnative.dev/)
- [Expo Documentation](https://docs.expo.dev/)

## 👤 Autor

**Alejandro** - TFG 2025

## 📄 Licencia

Este proyecto es parte de un Trabajo de Fin de Grado.

## 🙏 Agradecimientos

- Errbot community
- Supabase
- React Native / Expo teams
