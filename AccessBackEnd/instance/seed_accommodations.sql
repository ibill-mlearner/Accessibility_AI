-- Seed accommodations and prompt-link baseline data for AccessBackEnd MVP.
-- GPT IDEAS NOT FINAL SELECTIONS OR ACCESSIBLITY FEATURES
BEGIN TRANSACTION;

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'Simplified language', 'Use plain language and define technical terms with short explanations.', 1, 1, NULL, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE title = 'Simplified language'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'Bullet-point summaries', 'Respond with concise bullet points and a short recap at the end.', 1, 1, NULL, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE title = 'Bullet-point summaries'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'Dyslexia-friendly formatting', 'Use short paragraphs, strong headings, and avoid dense text blocks.', 1, 1, NULL, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE title = 'Dyslexia-friendly formatting'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'Extra spacing and pacing', 'Insert extra line spacing and split multi-step instructions into numbered steps.', 0, 1, NULL, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE title = 'Extra spacing and pacing'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'Read-aloud cues', 'Add punctuation and phrasing cues that make text easier for screen readers.', 0, 1, NULL, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE title = 'Read-aloud cues'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font size 14px', 'profile: Use a smaller but still accessible text size.', 1, 1, 14, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_size_px = 14
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font size 16px', 'profile: Use the default readable text size.', 1, 1, 16, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_size_px = 16
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font size 18px', 'profile: Use a larger text size for improved readability.', 1, 1, 18, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_size_px = 18
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font size 20px', 'profile: Use an extra-large text size for accessibility support.', 1, 1, 20, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_size_px = 20
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font size 24px', 'profile: Use maximum readability text size.', 1, 1, 24, NULL, NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_size_px = 24
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT
  'profile: Color profile: Deuteranopia-safe palette',
  'profile: Use deuteranopia-safe substitutions and CSS variables. Accent primary RGB(0, 114, 178), accent secondary RGB(230, 159, 0), success RGB(0, 158, 115), warning RGB(240, 228, 66), error RGB(213, 94, 0). Prefer hue contrast from blue/orange families with moderate chroma and avoid red/green-only distinctions.',
  1,
  0,
  NULL,
  NULL,
  'deuteranopia-safe'
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE title = 'profile: Color profile: Deuteranopia-safe palette'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font family: Sans-serif', 'profile: Prefer sans-serif typefaces for clearer character shapes at smaller sizes.', 1, 1, NULL, 'sans-serif', NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_family = 'sans-serif'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font family: Serif', 'profile: Prefer serif typefaces for users who track word forms more easily with serifs.', 1, 1, NULL, 'serif', NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_family = 'serif'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Font family: Monospace', 'profile: Use monospace fonts for consistent character spacing and code-heavy content.', 1, 1, NULL, 'monospace', NULL
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE font_family = 'monospace'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Color family: Protanopia-safe', 'profile: Use cyan/magenta-leaning contrasts and avoid red-dependent status indicators.', 1, 1, NULL, NULL, 'protanopia-safe'
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE color_family = 'protanopia-safe'
);

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family, color_family)
SELECT 'profile: Color family: Tritanopia-safe', 'profile: Use red/green contrasts with neutral backups and avoid blue-yellow-only distinctions.', 1, 1, NULL, NULL, 'tritanopia-safe'
WHERE NOT EXISTS (
  SELECT 1 FROM accommodations WHERE color_family = 'tritanopia-safe'
);

INSERT INTO system_prompts (instructor_id, class_id, text)
SELECT NULL, NULL, 'Global accessibility accommodations baseline prompt.'
WHERE NOT EXISTS (SELECT 1 FROM system_prompts WHERE id = 1);

INSERT INTO accommodations_id_system_prompts (accommodation_id, system_prompt_id)
SELECT a.id, 1
FROM accommodations AS a
WHERE a.title = 'Simplified language'
  AND NOT EXISTS (
    SELECT 1
    FROM accommodations_id_system_prompts AS link
    WHERE link.accommodation_id = a.id AND link.system_prompt_id = 1
  );

COMMIT;
