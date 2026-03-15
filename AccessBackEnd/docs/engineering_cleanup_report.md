# Engineering Cleanup Report (Config + AI pipeline path)

## Scope reviewed
- `app/services/ai_pipeline_v2`
- `app/api/v1/ai_model_catalog_routes.py`
- `app/config.py` environment parsing helpers

## Before
- Environment parsing helpers were centralized only in `app/config.py` and repeated in service-adjacent code.
- AI catalog/inventory paths did synchronous provider inventory fetches on each cache miss with coarse fixed TTL in service code.
- AI service factory used only broad `Mapping[str, Any]` config contract.

## After
- Added shared parsing helpers in `app/utils/env_config.py` and module-scoped typed config dataclasses colocated with owning modules.
- Added explicit `AIPipelineV2ModuleConfig` contract and retained dict adapter for migration fallback.
- Added timing spans and bounded parallel provider inventory fetch in AI pipeline service inventory path.
- Added timing metadata on `/api/v1/ai/catalog` responses to improve diagnostics.

## Efficiency wins
- Reduced repeated config-key lookups by resolving module config once at startup.
- Reduced serial provider inventory latency by parallelizing provider inventory fetch.
- Added cache TTL configurability (`AI_INVENTORY_CACHE_TTL_SECONDS`) to avoid repeated scans per request burst.
