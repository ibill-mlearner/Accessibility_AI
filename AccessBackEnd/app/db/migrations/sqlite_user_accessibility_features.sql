-- Migration intent:
-- Add the per-user accommodation preference table so accessibility choices can
-- be persisted without changing legacy user/accommodation rows.
CREATE TABLE IF NOT EXISTS user_accessibility_features (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  accommodation_id INTEGER NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT 0,
  CONSTRAINT uq_user_accessibility_feature UNIQUE (user_id, accommodation_id),
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(accommodation_id) REFERENCES accommodations(id)
);

CREATE INDEX IF NOT EXISTS ix_user_accessibility_features_user_id
  ON user_accessibility_features(user_id);

CREATE INDEX IF NOT EXISTS ix_user_accessibility_features_accommodation_id
  ON user_accessibility_features(accommodation_id);
