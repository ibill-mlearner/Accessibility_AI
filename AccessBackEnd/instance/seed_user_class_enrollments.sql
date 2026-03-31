-- Seed user/class enrollment relational data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO user_class_enrollments (user_id, class_id, active)
SELECT
  user_record.id,
  class_record.id,
  1
FROM users AS user_record
JOIN classes AS class_record
  ON class_record.name IN ('Soup Basics 101', 'Soup Lab')
WHERE user_record.email IN (
  'student.one.seed@example.com',
  'student.two.seed@example.com',
  'student.three.seed@example.com'
)
  AND NOT EXISTS (
    SELECT 1
    FROM user_class_enrollments AS enrollment_record
    WHERE enrollment_record.user_id = user_record.id
      AND enrollment_record.class_id = class_record.id
  );

COMMIT;
