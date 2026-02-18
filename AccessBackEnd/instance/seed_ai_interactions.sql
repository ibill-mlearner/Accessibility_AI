-- Seed AI interactions baseline data for AccessBackEnd MVP.

BEGIN TRANSACTION;

INSERT INTO ai_interactions (
  chat_id,
  accommodations_id_system_prompts_id,
  prompt,
  response_text,
  ai_model_id
)
SELECT
  (SELECT id FROM chats WHERE title = 'Chicken Noodle Soup - Starter Chat' LIMIT 1),
  (SELECT id FROM accommodations_id_system_prompts WHERE accommodation_id = 1 AND system_prompt_id = 1 LIMIT 1),
  'How can I start a basic chicken noodle soup?',
  'Start with broth, cooked chicken, carrots, celery, onion, noodles, and seasoning. Simmer vegetables first, then add chicken and noodles until tender.',
  (SELECT id FROM ai_models WHERE provider = 'huggingface_langchain' LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1 FROM ai_interactions
  WHERE chat_id = (SELECT id FROM chats WHERE title = 'Chicken Noodle Soup - Starter Chat' LIMIT 1)
    AND prompt = 'How can I start a basic chicken noodle soup?'
);

INSERT INTO ai_interactions (
  chat_id,
  accommodations_id_system_prompts_id,
  prompt,
  response_text,
  ai_model_id
)
SELECT
  (SELECT id FROM chats WHERE title = 'Chicken Noodle Soup - General User Chat' LIMIT 1),
  (SELECT id FROM accommodations_id_system_prompts WHERE accommodation_id = 1 AND system_prompt_id = 1 LIMIT 1),
  'What are easy variations for chicken noodle soup?',
  'Try adding garlic and herbs, swapping in rice for noodles, or including spinach near the end for a quick variation.',
  (SELECT id FROM ai_models WHERE provider = 'huggingface_langchain' LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1 FROM ai_interactions
  WHERE chat_id = (SELECT id FROM chats WHERE title = 'Chicken Noodle Soup - General User Chat' LIMIT 1)
    AND prompt = 'What are easy variations for chicken noodle soup?'
);

INSERT INTO ai_interactions (
  chat_id,
  accommodations_id_system_prompts_id,
  prompt,
  response_text,
  ai_model_id
)
SELECT
  (SELECT id FROM chats WHERE title = 'Chicken Noodle Soup - Instructor Demo' LIMIT 1),
  (SELECT id FROM accommodations_id_system_prompts WHERE accommodation_id = 1 AND system_prompt_id = 1 LIMIT 1),
  'How would you teach this recipe step-by-step?',
  'Demonstrate mise en place, explain simmer timing, model tasting and seasoning adjustments, then have students summarize each phase.',
  (SELECT id FROM ai_models WHERE provider = 'huggingface_langchain' LIMIT 1)
WHERE NOT EXISTS (
  SELECT 1 FROM ai_interactions
  WHERE chat_id = (SELECT id FROM chats WHERE title = 'Chicken Noodle Soup - Instructor Demo' LIMIT 1)
    AND prompt = 'How would you teach this recipe step-by-step?'
);

UPDATE chats
SET ai_interaction_id = (
  SELECT ai.id
  FROM ai_interactions ai
  WHERE ai.chat_id = chats.id
  ORDER BY ai.id DESC
  LIMIT 1
)
WHERE title IN (
  'Chicken Noodle Soup - Starter Chat',
  'Chicken Noodle Soup - General User Chat',
  'Chicken Noodle Soup - Instructor Demo'
)
  AND ai_interaction_id IS NULL
  AND EXISTS (SELECT 1 FROM ai_interactions ai WHERE ai.chat_id = chats.id);

COMMIT;
