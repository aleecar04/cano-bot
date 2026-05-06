ALTER TABLE commands
  DROP CONSTRAINT IF EXISTS commands_device_id_fkey,
  ADD CONSTRAINT commands_device_id_fkey
    FOREIGN KEY (device_id)
    REFERENCES devices(id)
    ON DELETE CASCADE;
