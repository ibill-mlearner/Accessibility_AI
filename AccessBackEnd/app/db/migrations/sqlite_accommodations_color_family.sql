ALTER TABLE accommodations
ADD COLUMN color_family TEXT;

INSERT INTO accommodations (title, details, active, displayable, font_size_px, color_family)
SELECT 'Color family: Deuteranopia-safe', 'Use blue/orange-anchored accents with strong luminance separation for red-green color vision differences.', 1, 1, NULL, 'deuteranopia-safe'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE color_family = 'deuteranopia-safe');

INSERT INTO accommodations (title, details, active, displayable, font_size_px, color_family)
SELECT 'Color family: Protanopia-safe', 'Use cyan/magenta-leaning contrasts and avoid red-dependent status indicators.', 1, 1, NULL, 'protanopia-safe'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE color_family = 'protanopia-safe');

INSERT INTO accommodations (title, details, active, displayable, font_size_px, color_family)
SELECT 'Color family: Tritanopia-safe', 'Use red/green contrasts with neutral backups and avoid blue-yellow-only distinctions.', 1, 1, NULL, 'tritanopia-safe'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE color_family = 'tritanopia-safe');
