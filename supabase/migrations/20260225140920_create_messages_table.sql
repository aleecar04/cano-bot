-- 1. Enum de status (estos sí son finitos)
CREATE TYPE command_status AS ENUM ('pending', 'sent', 'executed', 'failed');

-- 2. Usuarios
CREATE TABLE base_user (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  jid TEXT UNIQUE NOT NULL,
  xmpp_password TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Dispositivos
CREATE TABLE devices (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  owner_id UUID REFERENCES base_user(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  location TEXT,
  jid TEXT UNIQUE NOT NULL,
  is_online BOOLEAN DEFAULT false,
  last_seen_at TIMESTAMPTZ,
  registered_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Comandos (primero que messages porque messages lo referencia)
CREATE TABLE commands (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES base_user(id),
  device_id UUID REFERENCES devices(id),
  action TEXT NOT NULL,          -- "turn_on", "scan_network" etc, TEXT libre
  payload JSONB,                 -- {"brightness": 75} parámetros extra
  status command_status DEFAULT 'pending',
  xmpp_message_id TEXT,          -- para correlacionar respuesta del bot
  executed_at TIMESTAMPTZ,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Mensajes
CREATE TABLE messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  from_user_id UUID REFERENCES base_user(id),
  command_id UUID REFERENCES commands(id),
  body TEXT NOT NULL,
  response TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);