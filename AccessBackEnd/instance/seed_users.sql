-- Seed users and baseline reference data for AccessBackEnd MVP.
-- Default password for all seeded users: Password123!

BEGIN TRANSACTION;

INSERT INTO users (
  email,
  normalized_email,
  password_hash,
  role,
  created_at,
  updated_at,
  last_login_at,
  is_active,
  email_confirmed,
  lockout_end,
  access_failed_count,
  lockout_enabled,
  security_stamp
)
VALUES
  (
    'admin.seed@example.com',
    'admin.seed@example.com',
    'scrypt:32768:8:1$OF2fPI9HwmBfip03$07a3702c8aab2890728e86d0f6470ab62b73a2c1a9ab72871d6baf90e4d274125a1f8d484f352c5575cec869f464d97279b00cd94feb3405e7348de9737b9d10',
    'admin',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL,
    1,
    0,
    NULL,
    0,
    1,
    'transitional-' || lower(hex(randomblob(16)))
  ),
  (
    'instructor.seed@example.com',
    'instructor.seed@example.com',
    'scrypt:32768:8:1$ny9gwx01wD1UtYIQ$4bf419773b9ef7632b66065808d51a34bd28abef9898104017eeec9e53fcb1e36f3f02d2ca5b78eb97a3859e42f8f4d84738eae0d3d05db8bc35ae98237b16a2',
    'instructor',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL,
    1,
    0,
    NULL,
    0,
    1,
    'transitional-' || lower(hex(randomblob(16)))
  ),
  (
    'student.seed@example.com',
    'student.seed@example.com',
    'scrypt:32768:8:1$SgRFEPc0QdeD0MP4$1d86235a3a4f716caba8819f391421fa357928efb8effff91c6b7a74c483ce17562d6313385fa46c3ed77958353241b795d852bdb8cac3629c308ca27ad08f47',
    'student',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL,
    1,
    0,
    NULL,
    0,
    1,
    'transitional-' || lower(hex(randomblob(16)))
  ),
  (
    'general.seed@example.com',
    'general.seed@example.com',
    'scrypt:32768:8:1$Wno7y2lBycW3B3Jz$e12119fd8278e31423d49e1d98b7f300d7c0955ba81b51a2e44d87e58732f29f6e3b6a9c82b2b35d850aaa42aa94578fcbec1a06aa5f658737b0ae3d77a5d310',
    'student',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL,
    1,
    0,
    NULL,
    0,
    1,
    'transitional-' || lower(hex(randomblob(16)))
  )
ON CONFLICT(email) DO UPDATE SET
  normalized_email = excluded.normalized_email,
  password_hash = excluded.password_hash,
  role = excluded.role,
  updated_at = CURRENT_TIMESTAMP,
  is_active = excluded.is_active,
  email_confirmed = excluded.email_confirmed,
  lockout_end = excluded.lockout_end,
  access_failed_count = excluded.access_failed_count,
  lockout_enabled = excluded.lockout_enabled,
  security_stamp = 'transitional-' || lower(hex(randomblob(16)));

INSERT INTO ai_models (provider, active)
SELECT 'huggingface_langchain', 1
WHERE NOT EXISTS (SELECT 1 FROM ai_models WHERE provider = 'huggingface_langchain');

INSERT INTO accommodations (title, details, active)
SELECT ' ', ' ', 1
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE id = 1);

INSERT INTO system_prompts (instructor_id, class_id, text)
SELECT NULL, NULL, ' '
WHERE NOT EXISTS (SELECT 1 FROM system_prompts WHERE id = 1);

INSERT INTO accommodations_id_system_prompts (accommodation_id, system_prompt_id)
SELECT 1, 1
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations_id_system_prompts WHERE accommodation_id = 1 AND system_prompt_id = 1
);

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'Soup Basics 101',
  'Beginner discussion topics for making chicken noodle soup.',
  (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (SELECT 1 FROM classes WHERE name = 'Soup Basics 101' AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1));

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'Soup Lab',
  'Instructor-led walkthrough for a simple chicken noodle soup recipe.',
  (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (SELECT 1 FROM classes WHERE name = 'Soup Lab' AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1));

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments
  WHERE user_id = (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1)
    AND class_id = (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1)
);

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments
  WHERE user_id = (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1)
    AND class_id = (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id, ai_interaction_id)
SELECT
  'Chicken Noodle Soup - Starter Chat',
  'huggingface_langchain',
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1),
  NULL
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - Starter Chat'
    AND user_id = (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id, ai_interaction_id)
SELECT
  'Chicken Noodle Soup - General User Chat',
  'huggingface_langchain',
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1),
  NULL
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - General User Chat'
    AND user_id = (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id, ai_interaction_id)
SELECT
  'Chicken Noodle Soup - Instructor Demo',
  'huggingface_langchain',
  (SELECT id FROM classes WHERE name = 'Soup Lab' LIMIT 1),
  (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1),
  NULL
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - Instructor Demo'
    AND user_id = (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1)
);

COMMIT;
