-- Seed user/class enrollment relational data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'student.one.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments
  WHERE user_id = (SELECT id FROM users WHERE email = 'student.one.seed@example.com' LIMIT 1)
    AND class_id = (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1)
);

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'student.two.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments
  WHERE user_id = (SELECT id FROM users WHERE email = 'student.two.seed@example.com' LIMIT 1)
    AND class_id = (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1)
);

COMMIT;
