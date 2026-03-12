-- Seed per-user accessibility feature preferences.

BEGIN TRANSACTION;

INSERT INTO user_accessibility_features (user_id, accommodation_id, enabled)
SELECT u.id, a.id, 1
FROM users u
JOIN accommodations a ON a.title IN ('Simplified language', 'Bullet-point summaries')
WHERE u.email IN (
  'student.one.seed@example.com',
  'student.two.seed@example.com',
  'student.three.seed@example.com'
)
ON CONFLICT(user_id, accommodation_id) DO UPDATE SET enabled = excluded.enabled;

COMMIT;
