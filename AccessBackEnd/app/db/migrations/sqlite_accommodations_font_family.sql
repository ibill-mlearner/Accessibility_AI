ALTER TABLE accommodations
ADD COLUMN font_family TEXT;

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family)
SELECT 'profile: Font family: Sans-serif', 'profile: Prefer sans-serif typefaces for clearer character shapes at smaller sizes.', 1, 1, NULL, 'sans-serif'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_family = 'sans-serif');

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family)
SELECT 'profile: Font family: Serif', 'profile: Prefer serif typefaces for users who track word forms more easily with serifs.', 1, 1, NULL, 'serif'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_family = 'serif');

INSERT INTO accommodations (title, details, active, displayable, font_size_px, font_family)
SELECT 'profile: Font family: Monospace', 'profile: Use monospace fonts for consistent character spacing and code-heavy content.', 1, 1, NULL, 'monospace'
WHERE NOT EXISTS (SELECT 1 FROM accommodations WHERE font_family = 'monospace');
