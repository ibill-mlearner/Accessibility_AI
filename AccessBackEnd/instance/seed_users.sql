-- Seed users for AccessBackEnd.
-- Creates 1 account for each supported role (admin, instructor, student)
-- plus 1 additional general user account using the student role.
-- Also seeds simple sample classes/chats with a shared "chicken noodle soup" theme.
--
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
    'transitional-03f1ced2575577e88ce106f0c860438e'
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
    'transitional-ec92c8f17b92a85cfdf801aea88c92e0'
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
    'transitional-e4abacc32e3c064c5d626779a3193d6a'
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
    'transitional-237aa909aa970c55fe6ce68b070ee239'
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
  security_stamp = excluded.security_stamp;

INSERT INTO classes (role, name, description, instructor_id, term, section_code, external_class_key)
SELECT
  'student',
  'Soup Basics 101',
  'Beginner discussion topics for making chicken noodle soup.',
  (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1),
  '2025-SPRING',
  'A1',
  'SOUP-101-2025-SPRING-A1'
WHERE NOT EXISTS (SELECT 1 FROM classes WHERE external_class_key = 'SOUP-101-2025-SPRING-A1');

INSERT INTO classes (role, name, description, instructor_id, term, section_code, external_class_key)
SELECT
  'instructor',
  'Soup Lab',
  'Instructor-led walkthrough for a simple chicken noodle soup recipe.',
  (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1),
  '2025-SPRING',
  'L1',
  'SOUP-LAB-2025-SPRING-L1'
WHERE NOT EXISTS (SELECT 1 FROM classes WHERE external_class_key = 'SOUP-LAB-2025-SPRING-L1');


INSERT INTO user_class_enrollments (user_id, class_id, role, enrolled_at)
SELECT
  (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE external_class_key = 'SOUP-101-2025-SPRING-A1' LIMIT 1),
  'student',
  CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments
  WHERE user_id = (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1)
    AND class_id = (SELECT id FROM classes WHERE external_class_key = 'SOUP-101-2025-SPRING-A1' LIMIT 1)
);

INSERT INTO user_class_enrollments (user_id, class_id, role, enrolled_at)
SELECT
  (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE external_class_key = 'SOUP-101-2025-SPRING-A1' LIMIT 1),
  'student',
  CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments
  WHERE user_id = (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1)
    AND class_id = (SELECT id FROM classes WHERE external_class_key = 'SOUP-101-2025-SPRING-A1' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id)
SELECT
  'Chicken Noodle Soup - Starter Chat',
  'gpt-4o-mini',
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - Starter Chat'
    AND user_id = (SELECT id FROM users WHERE email = 'student.seed@example.com' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id)
SELECT
  'Chicken Noodle Soup - General User Chat',
  'gpt-4o-mini',
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - General User Chat'
    AND user_id = (SELECT id FROM users WHERE email = 'general.seed@example.com' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id)
SELECT
  'Chicken Noodle Soup - Instructor Demo',
  'gpt-4o-mini',
  (SELECT id FROM classes WHERE name = 'Soup Lab' LIMIT 1),
  (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - Instructor Demo'
    AND user_id = (SELECT id FROM users WHERE email = 'instructor.seed@example.com' LIMIT 1)
);

COMMIT;
