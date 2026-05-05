-- ═══════════════════════════════════════════════════════════════════════
-- CANO4 — Schema completo (estado actual)
-- Consolida todas las migraciones en un único fichero ejecutable
-- ═══════════════════════════════════════════════════════════════════════

-- ── Extensiones ──────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;

SET timezone = 'Europe/Madrid';

-- ── Tipos ────────────────────────────────────────────────────────────────
CREATE TYPE command_status AS ENUM ('pending', 'sent', 'executed', 'failed');

-- ── Usuarios ─────────────────────────────────────────────────────────────
CREATE TABLE base_user (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username     TEXT UNIQUE NOT NULL,
  first_name   TEXT,
  last_name    TEXT,
  avatar_url   TEXT,
  email        TEXT,
  is_active    BOOLEAN DEFAULT true,
  is_superuser BOOLEAN DEFAULT false,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── XMPP ─────────────────────────────────────────────────────────────────
CREATE TABLE xmpp_accounts (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID UNIQUE REFERENCES base_user(id) ON DELETE CASCADE,
  jid        TEXT UNIQUE NOT NULL,
  password   BYTEA NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION insert_xmpp_account(
    p_user_id UUID, p_jid TEXT, p_password TEXT, p_key TEXT
) RETURNS void AS $$
BEGIN
    INSERT INTO xmpp_accounts (user_id, jid, password)
    VALUES (p_user_id, p_jid, pgp_sym_encrypt(p_password, p_key));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_xmpp_password(
    p_user_id UUID, p_key TEXT
) RETURNS TEXT AS $$
DECLARE v_password TEXT;
BEGIN
    SELECT pgp_sym_decrypt(password, p_key) INTO v_password
    FROM xmpp_accounts WHERE user_id = p_user_id;
    RETURN v_password;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ── Casas ─────────────────────────────────────────────────────────────────
-- [NUEVO] name, bot_jid añadidos respecto al original
CREATE TABLE houses (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID REFERENCES base_user(id) ON DELETE CASCADE,
  name       TEXT DEFAULT 'Mi Casa',
  bot_jid    TEXT UNIQUE,                  -- [NUEVO] JID del bot que controla esta casa
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- [NUEVO] Miembros del hogar (modelo multi-usuario por casa)
CREATE TABLE house_members (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  house_id   UUID NOT NULL REFERENCES houses(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role       TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner', 'member')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (house_id, user_id)
);

-- [NUEVO] Códigos de invitación para unirse a una casa
CREATE TABLE house_invitations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  house_id   UUID NOT NULL REFERENCES houses(id) ON DELETE CASCADE,
  code       TEXT NOT NULL UNIQUE,
  created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX house_invitations_code_idx ON house_invitations(code);

-- ── Estructura del hogar ──────────────────────────────────────────────────
CREATE TABLE floors (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  house_id   UUID REFERENCES houses(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  level      INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rooms (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  floor_id   UUID REFERENCES floors(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT rooms_floor_id_name_key UNIQUE (floor_id, name)  -- [NUEVO] unicidad de nombre por planta
);

-- ── Dispositivos ──────────────────────────────────────────────────────────
-- [NUEVO] house_id (dispositivos pertenecen a la casa, no al usuario)
CREATE TABLE devices (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  owner_id      UUID REFERENCES base_user(id) ON DELETE CASCADE,
  house_id      UUID REFERENCES houses(id) ON DELETE SET NULL,  -- [NUEVO]
  name          TEXT NOT NULL,
  type          TEXT NOT NULL,
  driver        TEXT NOT NULL DEFAULT 'generic',
  ip            TEXT,
  mac           TEXT,
  ha_entity_id  TEXT,
  config        JSONB DEFAULT '{}',
  estado        JSONB DEFAULT '{}',
  is_online     BOOLEAN DEFAULT false,
  room_id       UUID REFERENCES rooms(id) ON DELETE SET NULL,
  registered_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  -- [NUEVO] unicidad basada en house_id en lugar de owner_id
  CONSTRAINT devices_house_id_mac_key         UNIQUE (house_id, mac),
  CONSTRAINT devices_house_id_ha_entity_id_key UNIQUE (house_id, ha_entity_id),
  CONSTRAINT devices_house_id_name_key         UNIQUE (house_id, name)  -- [NUEVO]
);

-- ── Home Assistant ────────────────────────────────────────────────────────
CREATE TABLE ha_integrations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID UNIQUE NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  ha_url     TEXT NOT NULL,
  token      TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE ha_integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY ha_integrations_owner ON ha_integrations USING (user_id = auth.uid());

-- ── Comandos ─────────────────────────────────────────────────────────────
CREATE TABLE commands (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id         UUID REFERENCES base_user(id),
  device_id       UUID REFERENCES devices(id),
  action          TEXT NOT NULL,
  payload         JSONB,
  status          command_status DEFAULT 'pending',
  xmpp_message_id TEXT,
  executed_at     TIMESTAMPTZ,
  error           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tareas programadas ────────────────────────────────────────────────────
-- [NUEVO] timezone añadido; estructura rediseñada (cron_expr, next_run_at, etc.)
CREATE TABLE schedules (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  device_id    UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  action       TEXT NOT NULL,
  payload      JSONB DEFAULT '{}',
  run_at       TIMESTAMPTZ,
  cron_expr    TEXT,
  next_run_at  TIMESTAMPTZ NOT NULL,
  is_recurring BOOLEAN DEFAULT FALSE,
  is_active    BOOLEAN DEFAULT TRUE,
  timezone     TEXT NOT NULL DEFAULT 'UTC',  -- [NUEVO]
  last_run_at  TIMESTAMPTZ,
  last_status  TEXT CHECK (last_status IN ('ok', 'error')),
  last_error   TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_schedules_user     ON schedules(user_id);
CREATE INDEX idx_schedules_next_run ON schedules(next_run_at) WHERE is_active = TRUE;

ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus tareas"       ON schedules FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Usuario crea sus tareas"     ON schedules FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Usuario actualiza sus tareas" ON schedules FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Usuario elimina sus tareas"  ON schedules FOR DELETE USING (user_id = auth.uid());

-- ── Favoritos ────────────────────────────────────────────────────────────
CREATE TABLE favorite_actions (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  device_id  UUID NOT NULL REFERENCES devices(id)   ON DELETE CASCADE,
  action     TEXT NOT NULL,
  payload    JSONB DEFAULT '{}',
  label      TEXT,
  position   INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT max_4_per_user UNIQUE (user_id, device_id, action)
);
CREATE INDEX idx_favorites_user ON favorite_actions(user_id);

ALTER TABLE favorite_actions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus favoritos"    ON favorite_actions FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Usuario crea sus favoritos"  ON favorite_actions FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Usuario elimina sus favoritos" ON favorite_actions FOR DELETE USING (user_id = auth.uid());

-- ── Conversaciones y mensajes ────────────────────────────────────────────
CREATE TABLE conversations (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID REFERENCES base_user(id) ON DELETE CASCADE,
  title      TEXT DEFAULT 'Nueva conversación',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE messages (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  from_user_id    UUID REFERENCES base_user(id),
  command_id      UUID REFERENCES commands(id),
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  xmpp_message_id TEXT,
  body            TEXT NOT NULL,
  response        TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_conversations_user    ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus conversaciones"      ON conversations FOR SELECT  USING (user_id = auth.uid());
CREATE POLICY "Usuario crea sus conversaciones"    ON conversations FOR INSERT  WITH CHECK (user_id = auth.uid());
CREATE POLICY "Usuario actualiza sus conversaciones" ON conversations FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Usuario borra sus conversaciones"   ON conversations FOR DELETE  USING (user_id = auth.uid());

-- ── Vistas ────────────────────────────────────────────────────────────────
CREATE VIEW houses_with_counts AS
SELECT h.*,
  (SELECT COUNT(*) FROM floors f WHERE f.house_id = h.id) AS total_floors,
  (SELECT COUNT(*) FROM devices d
   JOIN rooms r ON d.room_id = r.id
   JOIN floors f ON r.floor_id = f.id
   WHERE f.house_id = h.id) AS total_devices
FROM houses h;

CREATE VIEW floors_with_counts AS
SELECT f.*,
  (SELECT COUNT(*) FROM rooms r WHERE r.floor_id = f.id) AS total_rooms,
  (SELECT COUNT(*) FROM devices d
   JOIN rooms r ON d.room_id = r.id
   WHERE r.floor_id = f.id) AS total_devices
FROM floors f;

-- ── Seed: propietarios existentes → house_members ────────────────────────
INSERT INTO house_members (house_id, user_id, role)
SELECT id, user_id, 'owner' FROM houses WHERE user_id IS NOT NULL
ON CONFLICT (house_id, user_id) DO NOTHING;
