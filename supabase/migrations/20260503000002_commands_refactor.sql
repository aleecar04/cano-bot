-- ── commands: add source tracking ───────────────────────────────────────────
ALTER TABLE commands
  ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'direct'
    CHECK (source_type IN ('direct', 'conversation', 'favorite', 'schedule')),
  ADD COLUMN IF NOT EXISTS source_id   UUID;

-- ── schedules: add last_command_id, drop legacy audit columns ────────────────
ALTER TABLE schedules
  ADD COLUMN IF NOT EXISTS last_command_id UUID REFERENCES commands(id) ON DELETE SET NULL;

ALTER TABLE schedules
  DROP COLUMN IF EXISTS last_run_at,
  DROP COLUMN IF EXISTS last_status,
  DROP COLUMN IF EXISTS last_error,
  DROP COLUMN IF EXISTS run_at,
  DROP COLUMN IF EXISTS is_recurring;

-- ── indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_commands_source_type ON commands(source_type);
CREATE INDEX IF NOT EXISTS idx_commands_source_id   ON commands(source_id);
CREATE INDEX IF NOT EXISTS idx_commands_created_at  ON commands(created_at DESC);
