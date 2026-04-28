-- Migration intent:
-- Add `accommodations.displayable` to separate internally active profiles from
-- options that should appear in user-facing selection surfaces.
ALTER TABLE accommodations
ADD COLUMN displayable BOOLEAN NOT NULL DEFAULT 1;
