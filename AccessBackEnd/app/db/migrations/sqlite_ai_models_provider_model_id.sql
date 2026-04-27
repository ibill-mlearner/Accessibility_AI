-- Migration intent:
-- Rebuild `ai_models` so legacy SQLite databases gain a required `model_id`
-- and provider/model unique constraint used by current catalog selection logic.
ALTER TABLE ai_models RENAME TO ai_models_legacy;

CREATE TABLE ai_models (
    id INTEGER NOT NULL PRIMARY KEY,
    provider VARCHAR(80) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    source VARCHAR(80),
    path VARCHAR(512),
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ai_models_provider_model_id UNIQUE (provider, model_id)
);

INSERT INTO ai_models (
    id,
    provider,
    model_id,
    source,
    path,
    active
)
SELECT
    legacy.id,
    legacy.provider,
    COALESCE(NULLIF(TRIM(legacy.provider), ''), 'legacy-model-' || legacy.id) AS model_id,
    'legacy_provider_only' AS source,
    NULL AS path,
    COALESCE(legacy.active, 1) AS active
FROM ai_models_legacy AS legacy;

CREATE INDEX ix_ai_models_provider ON ai_models (provider);
CREATE INDEX ix_ai_models_model_id ON ai_models (model_id);

DROP TABLE ai_models_legacy;
