-- ── Extensiones ──────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;

SET timezone = 'Europe/Madrid';

-- ── Tipos ────────────────────────────────────────────────────────────────
CREATE TYPE command_status AS ENUM ('pending', 'sent', 'executed', 'failed');
CREATE TYPE device_driver  AS ENUM ('tuya', 'lg_tv', 'homeassistant', 'generic');

-- ── Usuarios ─────────────────────────────────────────────────────────────
CREATE TABLE base_user (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username    VARCHAR(50) UNIQUE NOT NULL,
  first_name  VARCHAR(100),
  last_name   VARCHAR(100),
  email       VARCHAR(255),
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
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

CREATE OR REPLACE FUNCTION update_xmpp_password(
    p_user_id UUID, p_password TEXT, p_key TEXT
) RETURNS void AS $$
BEGIN
    UPDATE xmpp_accounts
    SET password = pgp_sym_encrypt(p_password, p_key)
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ── Casas ─────────────────────────────────────────────────────────────────
CREATE TABLE houses (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name            VARCHAR(50) DEFAULT 'Mi Casa',
  bot_token_hash  TEXT UNIQUE NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_houses_bot_token_hash ON houses(bot_token_hash);

CREATE TABLE house_members (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  house_id   UUID NOT NULL REFERENCES houses(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  role       TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner', 'member')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (house_id, user_id)
);

CREATE TABLE house_invitations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  house_id   UUID NOT NULL REFERENCES houses(id) ON DELETE CASCADE,
  code       TEXT NOT NULL UNIQUE,
  created_by UUID NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at    TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX house_invitations_code_idx ON house_invitations(code);

-- ── Estructura del hogar ──────────────────────────────────────────────────
CREATE TABLE floors (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  house_id   UUID REFERENCES houses(id) ON DELETE CASCADE,
  name       VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE rooms (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  floor_id   UUID REFERENCES floors(id) ON DELETE CASCADE,
  name       VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT rooms_floor_id_name_key UNIQUE (floor_id, name)
);

-- ── Dispositivos ──────────────────────────────────────────────────────────
CREATE TABLE devices (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  owner_id      UUID REFERENCES base_user(id) ON DELETE CASCADE,
  house_id      UUID REFERENCES houses(id) ON DELETE CASCADE,
  name          VARCHAR(50) NOT NULL,
  type          VARCHAR(50) NOT NULL,
  driver        device_driver NOT NULL DEFAULT 'generic',
  ip            TEXT,
  mac           TEXT,
  ha_entity_id  TEXT,
  config        JSONB DEFAULT '{}',
  state         JSONB DEFAULT '{}',
  is_online     BOOLEAN DEFAULT false,
  room_id       UUID REFERENCES rooms(id) ON DELETE SET NULL,
  registered_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT devices_house_id_mac_key          UNIQUE (house_id, mac),
  CONSTRAINT devices_house_id_ha_entity_id_key UNIQUE (house_id, ha_entity_id),
  CONSTRAINT devices_house_id_name_key         UNIQUE (house_id, name)
);

-- ── Home Assistant ────────────────────────────────────────────────────────
CREATE TABLE ha_integrations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  house_id   UUID UNIQUE NOT NULL REFERENCES houses(id) ON DELETE CASCADE,
  ha_url     TEXT NOT NULL,
  token      TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ── Comandos ─────────────────────────────────────────────────────────────
CREATE TABLE commands (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id         UUID REFERENCES base_user(id) ON DELETE CASCADE,
  device_id       UUID REFERENCES devices(id) ON DELETE CASCADE,
  target_type     TEXT NOT NULL DEFAULT 'device'
                    CHECK (target_type IN ('device', 'system', 'info')),
  action          TEXT NOT NULL,
  payload         JSONB,
  status          command_status DEFAULT 'pending',
  executed_at     TIMESTAMPTZ,
  error           TEXT,
  result_data     JSONB,
  source_type     TEXT NOT NULL DEFAULT 'direct'
                    CHECK (source_type IN ('direct', 'conversation', 'favorite', 'schedule')),
  source_id       UUID,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT device_target_requires_device CHECK (
    (target_type = 'device'            AND device_id IS NOT NULL) OR
    (target_type IN ('system', 'info') AND device_id IS NULL)
  ),
  CONSTRAINT schedule_favorite_require_device CHECK (
    source_type NOT IN ('schedule', 'favorite') OR target_type = 'device'
  )
);
CREATE INDEX idx_commands_source_type ON commands(source_type);
CREATE INDEX idx_commands_source_id   ON commands(source_id);
CREATE INDEX idx_commands_created_at  ON commands(created_at DESC);

-- ── Tareas programadas ────────────────────────────────────────────────────
CREATE TABLE schedules (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  device_id       UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  name            VARCHAR(50) NOT NULL,
  action          TEXT NOT NULL,
  payload         JSONB DEFAULT '{}',
  cron_expr       TEXT,
  next_run_at     TIMESTAMPTZ NOT NULL,
  is_active       BOOLEAN DEFAULT TRUE,
  timezone        TEXT NOT NULL DEFAULT 'UTC',
  last_command_id UUID REFERENCES commands(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_schedules_user     ON schedules(user_id);
CREATE INDEX idx_schedules_next_run ON schedules(next_run_at) WHERE is_active = TRUE;

ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus tareas"        ON schedules FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Usuario crea sus tareas"      ON schedules FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Usuario actualiza sus tareas" ON schedules FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Usuario elimina sus tareas"   ON schedules FOR DELETE USING (user_id = auth.uid());

-- ── Favoritos ────────────────────────────────────────────────────────────
CREATE TABLE favorite_actions (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID NOT NULL REFERENCES base_user(id) ON DELETE CASCADE,
  device_id  UUID NOT NULL REFERENCES devices(id)   ON DELETE CASCADE,
  action     TEXT NOT NULL,
  payload    JSONB DEFAULT '{}',
  label      VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_favorite_per_user UNIQUE (user_id, device_id, action)
);
CREATE INDEX idx_favorites_user ON favorite_actions(user_id);

ALTER TABLE favorite_actions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus favoritos"      ON favorite_actions FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Usuario crea sus favoritos"    ON favorite_actions FOR INSERT WITH CHECK (user_id = auth.uid());
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
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  command_id      UUID REFERENCES commands(id),
  body            TEXT NOT NULL,
  response        TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_conversations_user    ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus conversaciones"        ON conversations FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Usuario crea sus conversaciones"      ON conversations FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Usuario actualiza sus conversaciones" ON conversations FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Usuario borra sus conversaciones"     ON conversations FOR DELETE USING (user_id = auth.uid());

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuario ve sus mensajes"        ON messages FOR SELECT
  USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));
CREATE POLICY "Usuario crea sus mensajes"      ON messages FOR INSERT
  WITH CHECK (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));
CREATE POLICY "Usuario actualiza sus mensajes" ON messages FOR UPDATE
  USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));
CREATE POLICY "Usuario borra sus mensajes"     ON messages FOR DELETE
  USING (conversation_id IN (SELECT id FROM conversations WHERE user_id = auth.uid()));

ALTER PUBLICATION supabase_realtime ADD TABLE messages;

-- ── Notificaciones push ──────────────────────────────────────────────────
CREATE TABLE push_subscriptions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL,
  endpoint   TEXT NOT NULL UNIQUE,
  p256dh     TEXT NOT NULL,
  auth       TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX push_subscriptions_user_id_idx ON push_subscriptions(user_id);


-- ── Grants para service_role (necesarios en entornos frescos como CI) ────
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;
