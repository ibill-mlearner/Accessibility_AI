-- Seed user/class enrollment relational data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'student.one.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'BIOL 110: Foundations of Cell Biology' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments AS enrollment_record
  WHERE enrollment_record.user_id = (SELECT id FROM users WHERE email = 'student.one.seed@example.com' LIMIT 1)
    AND enrollment_record.class_id = (SELECT id FROM classes WHERE name = 'BIOL 110: Foundations of Cell Biology' LIMIT 1)
);

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'student.two.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'CS 220: Data Structures and Algorithms' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments AS enrollment_record
  WHERE enrollment_record.user_id = (SELECT id FROM users WHERE email = 'student.two.seed@example.com' LIMIT 1)
    AND enrollment_record.class_id = (SELECT id FROM classes WHERE name = 'CS 220: Data Structures and Algorithms' LIMIT 1)
);

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  (SELECT id FROM users WHERE email = 'student.three.seed@example.com' LIMIT 1),
  (SELECT id FROM classes WHERE name = 'MATH 251: Calculus I' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM user_class_enrollments AS enrollment_record
  WHERE enrollment_record.user_id = (SELECT id FROM users WHERE email = 'student.three.seed@example.com' LIMIT 1)
    AND enrollment_record.class_id = (SELECT id FROM classes WHERE name = 'MATH 251: Calculus I' LIMIT 1)
);

COMMIT;
