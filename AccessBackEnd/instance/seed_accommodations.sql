-- Seed accommodations and prompt-link baseline data for AccessBackEnd MVP.

BEGIN TRANSACTION;

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

COMMIT;
