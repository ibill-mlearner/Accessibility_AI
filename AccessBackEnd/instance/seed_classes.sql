-- Seed classes baseline data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'Soup Basics 101',
  'Beginner discussion topics for making chicken noodle soup.',
  (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM classes
  WHERE name = 'Soup Basics 101'
    AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1)
);

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'Soup Lab',
  'Instructor-led walkthrough for a simple chicken noodle soup recipe.',
  (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM classes
  WHERE name = 'Soup Lab'
    AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1)
);

COMMIT;
