-- Seed classes baseline data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'BIOL 110: Foundations of Cell Biology',
  'Introductory biology course covering cell structure, genetics, and core lab safety expectations.',
  (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM classes
  WHERE name = 'BIOL 110: Foundations of Cell Biology'
    AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1)
);

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'CS 220: Data Structures and Algorithms',
  'Intermediate computer science class focused on complexity analysis, trees, hash tables, and graph traversal.',
  (SELECT id FROM users WHERE email = 'instructor.two.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM classes
  WHERE name = 'CS 220: Data Structures and Algorithms'
    AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.two.seed@example.com' LIMIT 1)
);

INSERT INTO classes (name, description, instructor_id, active)
SELECT
  'MATH 251: Calculus I',
  'First-term calculus emphasizing limits, derivatives, and real-world optimization problems.',
  (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1),
  1
WHERE NOT EXISTS (
  SELECT 1
  FROM classes
  WHERE name = 'MATH 251: Calculus I'
    AND instructor_id = (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1)
);

COMMIT;