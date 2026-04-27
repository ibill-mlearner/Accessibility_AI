-- Migration intent:
-- Add `accommodations.font_size_px` with guarded allowed values and seed
-- profile rows so UI and prompt assembly can reference explicit size presets.
ALTER TABLE accommodations
ADD COLUMN font_size_px INTEGER CHECK (font_size_px IN (14, 16, 18, 20, 24));

INSERT INTO accommodations (title, details, active, font_size_px)
SELECT 'profile: Font size 14px', 'profile: Use a smaller but still accessible text size.', 1, 14
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_size_px = 14);

INSERT INTO accommodations (title, details, active, font_size_px)
SELECT 'profile: Font size 16px', 'profile: Use the default readable text size.', 1, 16
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_size_px = 16);

INSERT INTO accommodations (title, details, active, font_size_px)
SELECT 'profile: Font size 18px', 'profile: Use a larger text size for improved readability.', 1, 18
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_size_px = 18);

INSERT INTO accommodations (title, details, active, font_size_px)
SELECT 'profile: Font size 20px', 'profile: Use an extra-large text size for accessibility support.', 1, 20
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_size_px = 20);

INSERT INTO accommodations (title, details, active, font_size_px)
SELECT 'profile: Font size 24px', 'profile: Use maximum readability text size.', 1, 24
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_size_px = 24);
