ALTER TABLE accommodations
ADD COLUMN font_family TEXT;

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family)
SELECT 'Font family: Sans-serif', 'standard; Prefer sans-serif typefaces for clearer character shapes at smaller sizes.', 1, 1, NULL, 'sans-serif'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_family = 'sans-serif');

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family)
SELECT 'Font family: Serif', 'standard; Prefer serif typefaces for users who track word forms more easily with serifs.', 1, 1, NULL, 'serif'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_family = 'serif');

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family)
SELECT 'Font family: Monospace', 'standard; Use monospace fonts for consistent character spacing and code-heavy content.', 1, 1, NULL, 'monospace'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_family = 'monospace');
