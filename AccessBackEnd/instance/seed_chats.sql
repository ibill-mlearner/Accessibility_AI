-- Seed chats baseline data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO chats (title, model, class_id, user_id, ai_interaction_id)
SELECT
  'Chicken Noodle Soup - Starter Chat',
  'huggingface_langchain',
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  (SELECT id FROM users WHERE email = 'student.one.seed@example.com' LIMIT 1),
  NULL
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - Starter Chat'
    AND user_id = (SELECT id FROM users WHERE email = 'student.one.seed@example.com' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id, ai_interaction_id)
SELECT
  'Chicken Noodle Soup - General User Chat',
  'huggingface_langchain',
  (SELECT id FROM classes WHERE name = 'Soup Basics 101' LIMIT 1),
  (SELECT id FROM users WHERE email = 'student.two.seed@example.com' LIMIT 1),
  NULL
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - General User Chat'
    AND user_id = (SELECT id FROM users WHERE email = 'student.two.seed@example.com' LIMIT 1)
);

INSERT INTO chats (title, model, class_id, user_id, ai_interaction_id)
SELECT
  'Chicken Noodle Soup - Instructor Demo',
  'huggingface_langchain',
  (SELECT id FROM classes WHERE name = 'Soup Lab' LIMIT 1),
  (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1),
  NULL
WHERE NOT EXISTS (
  SELECT 1
  FROM chats
  WHERE title = 'Chicken Noodle Soup - Instructor Demo'
    AND user_id = (SELECT id FROM users WHERE email = 'instructor.one.seed@example.com' LIMIT 1)
);

COMMIT;
