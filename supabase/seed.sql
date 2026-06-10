\set xmpp_key '8mfCXFFyowyTReEM44WqAxrIL0kmln_2gux_BfsWAg8'

-- UUIDs fijos para poder re-ejecutar el seed de forma idempotente
\set uid_admin   'a0000000-0000-0000-0000-000000000001'
\set uid_owner   'a0000000-0000-0000-0000-000000000002'
\set uid_member  'a0000000-0000-0000-0000-000000000003'

\set uid_house   'b0000000-0000-0000-0000-000000000001'
\set uid_floor0  'c0000000-0000-0000-0000-000000000001'
\set uid_floor1  'c0000000-0000-0000-0000-000000000002'
\set uid_room_s  'd0000000-0000-0000-0000-000000000001'  -- Salón
\set uid_room_k  'd0000000-0000-0000-0000-000000000002'  -- Cocina
\set uid_room_d  'd0000000-0000-0000-0000-000000000003'  -- Dormitorio

\set uid_dev_luz      'e0000000-0000-0000-0000-000000000001'
\set uid_dev_tv       'e0000000-0000-0000-0000-000000000002'
\set uid_dev_enchufe  'e0000000-0000-0000-0000-000000000003'
\set uid_dev_sensor   'e0000000-0000-0000-0000-000000000004'

\set uid_conv    'f0000000-0000-0000-0000-000000000001'
\set uid_sched1  '10000000-0000-0000-0000-000000000001'
\set uid_sched2  '10000000-0000-0000-0000-000000000002'
\set uid_fav1    '20000000-0000-0000-0000-000000000001'
\set uid_fav2    '20000000-0000-0000-0000-000000000002'
\set uid_cmd1    '30000000-0000-0000-0000-000000000001'
\set uid_cmd2    '30000000-0000-0000-0000-000000000002'
\set uid_cmd3    '30000000-0000-0000-0000-000000000003'
\set uid_msg1    '40000000-0000-0000-0000-000000000001'
\set uid_msg2    '40000000-0000-0000-0000-000000000002'
\set uid_msg3    '40000000-0000-0000-0000-000000000003'


-- ── 1. Usuarios en auth.users ────────────────────────────────────────────────
INSERT INTO auth.users (
    id, instance_id, aud, role, email,
    encrypted_password, email_confirmed_at,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, email_change, email_change_token_new, recovery_token
) VALUES
    (
        :'uid_admin', '00000000-0000-0000-0000-000000000000',
        'authenticated', 'authenticated', 'cano-admin@cano4.dev',
        crypt('Cano-Bot2026!', gen_salt('bf')), NOW(),
        '{"provider":"email","providers":["email"]}', '{}',
        NOW(), NOW(), '', '', '', ''
    ),
    (
        :'uid_owner', '00000000-0000-0000-0000-000000000000',
        'authenticated', 'authenticated', 'owner@cano4.dev',
        crypt('Owner-2026!', gen_salt('bf')), NOW(),
        '{"provider":"email","providers":["email"]}', '{}',
        NOW(), NOW(), '', '', '', ''
    ),
    (
        :'uid_member', '00000000-0000-0000-0000-000000000000',
        'authenticated', 'authenticated', 'member@cano4.dev',
        crypt('Member-2026!', gen_salt('bf')), NOW(),
        '{"provider":"email","providers":["email"]}', '{}',
        NOW(), NOW(), '', '', '', ''
    )
ON CONFLICT (id) DO NOTHING;


-- ── 2. Perfiles en base_user ─────────────────────────────────────────────────
INSERT INTO base_user (id, username, first_name, last_name, email, is_superuser, is_active)
VALUES
    (:'uid_admin',  'cano-admin',   'Cano',    'Admin',    'cano-admin@cano4.dev', true,  true),
    (:'uid_owner',  'propietario',  'Carlos',  'García',   'owner@cano4.dev',      false, true),
    (:'uid_member', 'miembro',      'María',   'López',    'member@cano4.dev',     false, true)
ON CONFLICT (id) DO NOTHING;


-- ── 3. Cuentas XMPP (contraseñas ficticias cifradas) ────────────────────────
-- El bot no podrá autenticarlas en el servidor XMPP real, pero la BD queda coherente.
SELECT insert_xmpp_account(:'uid_admin',  'cano-admin@xmpp.aleecr.es',   'seed_admin_pass',  :'xmpp_key')
WHERE NOT EXISTS (SELECT 1 FROM xmpp_accounts WHERE user_id = :'uid_admin');

SELECT insert_xmpp_account(:'uid_owner',  'propietario@xmpp.aleecr.es',  'seed_owner_pass',  :'xmpp_key')
WHERE NOT EXISTS (SELECT 1 FROM xmpp_accounts WHERE user_id = :'uid_owner');

SELECT insert_xmpp_account(:'uid_member', 'miembro@xmpp.aleecr.es',      'seed_member_pass', :'xmpp_key')
WHERE NOT EXISTS (SELECT 1 FROM xmpp_accounts WHERE user_id = :'uid_member');


-- ── 4. Casa ──────────────────────────────────────────────────────────────────
-- bot_token_hash: SHA-256 del bot_token de demo ('seed_demo_bot_token').
-- En producción este valor lo genera el backend al ejecutar la rotación;
-- aquí lo fijamos para que el seed sea idempotente.
INSERT INTO houses (id, name, bot_token_hash)
VALUES (
    :'uid_house',
    'Casa Demo',
    encode(digest('seed_demo_bot_token', 'sha256'), 'hex')
)
ON CONFLICT (id) DO NOTHING;


-- ── 5. Miembros del hogar ────────────────────────────────────────────────────
INSERT INTO house_members (house_id, user_id, role)
VALUES
    (:'uid_house', :'uid_owner',  'owner'),
    (:'uid_house', :'uid_member', 'member')
ON CONFLICT (house_id, user_id) DO NOTHING;


-- ── 6. Plantas ───────────────────────────────────────────────────────────────
INSERT INTO floors (id, house_id, name)
VALUES
    (:'uid_floor0', :'uid_house', 'Planta Baja'),
    (:'uid_floor1', :'uid_house', 'Primera Planta')
ON CONFLICT (id) DO NOTHING;


-- ── 7. Habitaciones ──────────────────────────────────────────────────────────
INSERT INTO rooms (id, floor_id, name)
VALUES
    (:'uid_room_s', :'uid_floor0', 'Salón'),
    (:'uid_room_k', :'uid_floor0', 'Cocina'),
    (:'uid_room_d', :'uid_floor1', 'Dormitorio Principal')
ON CONFLICT (id) DO NOTHING;


-- ── 8. Dispositivos ──────────────────────────────────────────────────────────
-- Luz Salón: datos reales del dispositivo Tuya del proyecto
INSERT INTO devices (id, owner_id, house_id, name, type, driver, ip, mac, room_id, is_online, estado, config)
VALUES (
    :'uid_dev_luz', :'uid_owner', :'uid_house',
    'Luz Salón', 'Luz', 'tuya',
    '192.168.0.178', '00:33:7a:d3:bb:9e', :'uid_room_s',
    true,
    '{"power":"on","brightness":1000,"color_temp":1000,"mode":"white"}',
    '{"dev_id":"bf4c45b651d39c6a986wrm","local_key":"u757pAs#@P(skJtP","version":"3.5"}'
) ON CONFLICT (id) DO NOTHING;

-- TV Salón: SmartTV LG (simulado)
INSERT INTO devices (id, owner_id, house_id, name, type, driver, ip, mac, room_id, is_online, estado, config)
VALUES (
    :'uid_dev_tv', :'uid_owner', :'uid_house',
    'TV Salón', 'SmartTV', 'lg_tv',
    '192.168.0.50', '00:aa:bb:cc:dd:01', :'uid_room_s',
    false,
    '{"power":"off","volume":20,"muted":false}',
    '{"model":"LG OLED55"}'
) ON CONFLICT (id) DO NOTHING;

-- Enchufe Cocina: Tuya (simulado)
INSERT INTO devices (id, owner_id, house_id, name, type, driver, ip, mac, room_id, is_online, estado, config)
VALUES (
    :'uid_dev_enchufe', :'uid_owner', :'uid_house',
    'Enchufe Cocina', 'Enchufe', 'tuya',
    '192.168.0.60', '00:aa:bb:cc:dd:02', :'uid_room_k',
    true,
    '{"power":"off"}',
    '{"channel":0}'
) ON CONFLICT (id) DO NOTHING;

-- Sensor Dormitorio: Tuya temperatura/humedad (simulado)
INSERT INTO devices (id, owner_id, house_id, name, type, driver, ip, mac, room_id, is_online, estado, config)
VALUES (
    :'uid_dev_sensor', :'uid_owner', :'uid_house',
    'Sensor Temperatura', 'Sensor', 'tuya',
    '192.168.0.75', '00:aa:bb:cc:dd:03', :'uid_room_d',
    true,
    '{"temperature":21.5,"humidity":55}',
    '{"dev_id":"sensor_demo_001","local_key":"demo_key_sensor_01","version":"3.3"}'
) ON CONFLICT (id) DO NOTHING;


-- ── 9. Favoritos ─────────────────────────────────────────────────────────────
INSERT INTO favorite_actions (id, user_id, device_id, action, payload, label)
VALUES
    (:'uid_fav1', :'uid_owner', :'uid_dev_luz', 'encender', '{}', 'Encender Luz Salón'),
    (:'uid_fav2', :'uid_owner', :'uid_dev_tv',  'apagar',   '{}', 'Apagar TV Salón')
ON CONFLICT (id) DO NOTHING;


-- ── 10. Tareas programadas ───────────────────────────────────────────────────

-- IDs adicionales para las nuevas tareas
\set uid_sched3  'f0000000-0000-0000-0000-000000000003'
\set uid_sched4  'f0000000-0000-0000-0000-000000000004'
\set uid_sched5  'f0000000-0000-0000-0000-000000000005'
\set uid_cmd_s1  'f0000000-0000-0000-0000-000000000011'
\set uid_cmd_s2  'f0000000-0000-0000-0000-000000000012'

-- [OWNER] Recurrente activa: apagar luces cada noche a las 23:00
INSERT INTO schedules (id, user_id, device_id, name, action, payload, cron_expr, next_run_at, is_active, timezone)
VALUES (
    :'uid_sched1', :'uid_owner', :'uid_dev_luz',
    'Apagar luces de noche', 'apagar', '{}',
    '0 23 * * *',
    (NOW() AT TIME ZONE 'Europe/Madrid')::date + interval '23 hours',
    true, 'Europe/Madrid'
) ON CONFLICT (id) DO NOTHING;

-- [OWNER] Recurrente activa: encender luz L-V a las 7:00
INSERT INTO schedules (id, user_id, device_id, name, action, payload, cron_expr, next_run_at, is_active, timezone)
VALUES (
    :'uid_sched2', :'uid_owner', :'uid_dev_luz',
    'Encender luz al amanecer (L-V)', 'encender', '{}',
    '0 7 * * 1-5',
    (NOW() AT TIME ZONE 'Europe/Madrid')::date + interval '7 hours',
    true, 'Europe/Madrid'
) ON CONFLICT (id) DO NOTHING;

-- [OWNER] Puntual COMPLETADA (is_active=false, sin cron) → muestra badge "Completada"
-- Primero el comando asociado
INSERT INTO commands (id, user_id, device_id, action, payload, status, source_type, executed_at)
VALUES (
    :'uid_cmd_s1', :'uid_owner', :'uid_dev_tv', 'apagar', '{}', 'executed', 'schedule',
    NOW() - interval '3 hours'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO schedules (id, user_id, device_id, name, action, payload, cron_expr, next_run_at, is_active, last_command_id, timezone)
VALUES (
    :'uid_sched3', :'uid_owner', :'uid_dev_tv',
    'Apagar TV (ejecución única)', 'apagar', '{}',
    NULL,
    NOW() - interval '3 hours',
    false, :'uid_cmd_s1', 'Europe/Madrid'
) ON CONFLICT (id) DO NOTHING;

-- [OWNER] Puntual FALLIDA (is_active=false, sin cron) → también "Completada" pero último estado=Error
INSERT INTO commands (id, user_id, device_id, action, payload, status, source_type, executed_at, error)
VALUES (
    :'uid_cmd_s2', :'uid_owner', :'uid_dev_enchufe', 'encender', '{}', 'failed', 'schedule',
    NOW() - interval '1 hour', 'Dispositivo no responde'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO schedules (id, user_id, device_id, name, action, payload, cron_expr, next_run_at, is_active, last_command_id, timezone)
VALUES (
    :'uid_sched4', :'uid_owner', :'uid_dev_enchufe',
    'Encender enchufe (falló)', 'encender', '{}',
    NULL,
    NOW() - interval '1 hour',
    false, :'uid_cmd_s2', 'Europe/Madrid'
) ON CONFLICT (id) DO NOTHING;

-- [MEMBER] Tarea del miembro → aparece con candado para el owner si accede como member,
--          y con color ámbar/candado para el owner si lo ven los miembros
INSERT INTO schedules (id, user_id, device_id, name, action, payload, cron_expr, next_run_at, is_active, timezone)
VALUES (
    :'uid_sched5', :'uid_member', :'uid_dev_luz',
    'Brillo suave por la noche', 'brillo', '{"valor":30}',
    '0 22 * * *',
    (NOW() AT TIME ZONE 'Europe/Madrid')::date + interval '22 hours',
    true, 'Europe/Madrid'
) ON CONFLICT (id) DO NOTHING;


-- ── 11. Comandos de ejemplo ──────────────────────────────────────────────────
INSERT INTO commands (id, user_id, device_id, action, payload, status, source_type, executed_at)
VALUES
    (:'uid_cmd1', :'uid_owner', :'uid_dev_luz',     'encender', '{}',                  'executed', 'conversation', NOW() - interval '2 hours'),
    (:'uid_cmd2', :'uid_owner', :'uid_dev_tv',      'apagar',   '{}',                  'executed', 'direct',       NOW() - interval '1 hour'),
    (:'uid_cmd3', :'uid_owner', :'uid_dev_enchufe', 'encender', '{"valor":100}',       'failed',   'favorite',     NOW() - interval '30 minutes')
ON CONFLICT (id) DO NOTHING;


-- ── 12. Conversación y mensajes ──────────────────────────────────────────────
INSERT INTO conversations (id, user_id, title)
VALUES (:'uid_conv', :'uid_owner', 'Demo: Control por chat')
ON CONFLICT (id) DO NOTHING;

INSERT INTO messages (id, conversation_id, command_id, body, response)
VALUES
    (
        :'uid_msg1', :'uid_conv', :'uid_cmd1',
        'enciende la luz del salón',
        'Luz Salón: encender ejecutado.'
    ),
    (
        :'uid_msg2', :'uid_conv', :'uid_cmd2',
        'lista mis dispositivos',
        '{"tipo":"device_list","dispositivos":[{"name":"Luz Salón","type":"Luz","is_online":true,"estado":{"power":"on","brightness":1000}},{"name":"TV Salón","type":"SmartTV","is_online":false,"estado":{"power":"off","volume":20}},{"name":"Enchufe Cocina","type":"Enchufe","is_online":true,"estado":{"power":"off"}},{"name":"Sensor Temperatura","type":"Sensor","is_online":true,"estado":{"temperature":21.5,"humidity":55}}],"total":4}'
    ),
    (
        :'uid_msg3', :'uid_conv', :'uid_cmd3',
        'apaga la tele',
        'TV Salón: apagar ejecutado.'
    )
ON CONFLICT (id) DO NOTHING;
