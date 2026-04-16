-- Extensiones
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tipos
CREATE TYPE command_status AS ENUM ('pending', 'sent', 'executed', 'failed');

-- Usuarios
CREATE TABLE base_user (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  avatar_url TEXT,
  email TEXT,
  is_active BOOLEAN DEFAULT true,
  is_superuser BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Credenciales XMPP
CREATE TABLE xmpp_accounts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID UNIQUE REFERENCES base_user(id) ON DELETE CASCADE,
  jid TEXT UNIQUE NOT NULL,
  password BYTEA NOT NULL,  -- BYTEA para almacenar el cifrado correctamente
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Funciones de cifrado XMPP
CREATE OR REPLACE FUNCTION insert_xmpp_account(
    p_user_id UUID, 
    p_jid TEXT, 
    p_password TEXT, 
    p_key TEXT
) RETURNS void AS $$
BEGIN
    INSERT INTO xmpp_accounts (user_id, jid, password)
    VALUES (p_user_id, p_jid, pgp_sym_encrypt(p_password, p_key));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_xmpp_password(
    p_user_id UUID,
    p_key TEXT
) RETURNS TEXT AS $$
DECLARE
    v_password TEXT;
BEGIN
    SELECT pgp_sym_decrypt(password, p_key)
    INTO v_password
    FROM xmpp_accounts
    WHERE user_id = p_user_id;
    RETURN v_password;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Casas
CREATE TABLE houses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES base_user(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Plantas
CREATE TABLE floors (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  house_id UUID REFERENCES houses(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  level INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Habitaciones
CREATE TABLE rooms (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  floor_id UUID REFERENCES floors(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dispositivos
CREATE TABLE devices (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  owner_id      UUID REFERENCES base_user(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  type          TEXT NOT NULL,
  driver        TEXT NOT NULL DEFAULT 'homeassistant',
  ip            TEXT,
  mac           TEXT,
  ha_entity_id  TEXT,
  config        JSONB DEFAULT '{}',
  estado        JSONB DEFAULT '{}',
  is_online     BOOLEAN DEFAULT false,
  room_id       UUID REFERENCES rooms(id) ON DELETE SET NULL,
  registered_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT devices_owner_mac_key UNIQUE (owner_id, mac),
  CONSTRAINT devices_owner_ha_entity_id_key UNIQUE (owner_id, ha_entity_id)
);

CREATE TABLE ha_integrations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID UNIQUE REFERENCES base_user(id) ON DELETE CASCADE,
  ha_url TEXT NOT NULL,
  token TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comandos
CREATE TABLE commands (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES base_user(id),
  device_id UUID REFERENCES devices(id),
  action TEXT NOT NULL,
  payload JSONB,
  status command_status DEFAULT 'pending',
  xmpp_message_id TEXT,
  executed_at TIMESTAMPTZ,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE schedules (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES base_user(id),
  command_id UUID REFERENCES commands(id),
  is_active BOOLEAN DEFAULT true,
  time_scheduled TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversaciones
CREATE TABLE conversations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES base_user(id) ON DELETE CASCADE,
  title TEXT DEFAULT 'Nueva conversación',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mensajes
CREATE TABLE messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  from_user_id UUID REFERENCES base_user(id),
  command_id UUID REFERENCES commands(id),
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  xmpp_message_id TEXT,
  body TEXT NOT NULL,
  response TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vistas
CREATE VIEW houses_with_counts AS
SELECT 
    h.*,
    (SELECT COUNT(*) FROM floors f WHERE f.house_id = h.id) as total_floors,
    (SELECT COUNT(*) FROM devices d 
     JOIN rooms r ON d.room_id = r.id 
     JOIN floors f ON r.floor_id = f.id 
     WHERE f.house_id = h.id) as total_devices
FROM houses h;

CREATE VIEW floors_with_counts AS
SELECT 
    f.*,
    (SELECT COUNT(*) FROM rooms r WHERE r.floor_id = f.id) as total_rooms,
    (SELECT COUNT(*) FROM devices d 
     JOIN rooms r ON d.room_id = r.id 
     WHERE r.floor_id = f.id) as total_devices
FROM floors f;

-- Índices
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

-- RLS Conversaciones
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Usuario ve sus conversaciones"
  ON conversations FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "Usuario crea sus conversaciones"
  ON conversations FOR INSERT
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Usuario actualiza sus conversaciones"
  ON conversations FOR UPDATE
  USING (user_id = auth.uid());

CREATE POLICY "Usuario borra sus conversaciones"
  ON conversations FOR DELETE
  USING (user_id = auth.uid());