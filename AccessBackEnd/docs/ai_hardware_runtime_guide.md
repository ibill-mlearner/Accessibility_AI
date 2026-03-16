# GPU Runtime Implementation Plan (AI Models)

This document is a **build plan** for adding reliable GPU execution paths for AI models in this project.

## Goal

Enable model inference to use GPU when available, with safe fallback to CPU, predictable config, and measurable latency improvements.

## Scope (what we are implementing)

1. Runtime config for device selection (`cpu` vs `gpu`).
2. Provider-level GPU wiring (Hugging Face first, Ollama verification second).
3. Preflight checks at startup to confirm GPU readiness.
4. Model-family routing rules based on available VRAM.
5. Observability + rollout gates (latency/error checks).

---

## Required config keys (from `app/config.py`)

Use these existing keys as the baseline for GPU rollout:

- `AI_PROVIDER`
- `AI_MODEL_NAME`
- `AI_HUGGINGFACE_CACHE_DIR`
- `AI_HUGGINGFACE_ALLOW_DOWNLOAD`
- `AI_TIMEOUT_SECONDS`
- `AI_OLLAMA_ENDPOINT`
- `AI_OLLAMA_MODEL`

### Add these new keys

- `AI_DEVICE_POLICY=auto|cpu|gpu`
  - `auto` = use GPU if available, else CPU.
- `AI_MIN_FREE_VRAM_GB=<number>`
  - minimum free VRAM required before selecting GPU path.
- `AI_GPU_WARMUP_ENABLED=true|false`
  - optional warmup call on startup.

---

## Implementation phases

## Phase 1 — Device policy plumbing

- [ ] Add new config fields to `AccessBackEnd/app/config.py`.
- [ ] Surface selected device in startup logs.
- [ ] Keep default behavior backward-compatible (`auto`).

**Done when:** app can report selected device policy and resolved runtime target.

## Phase 2 — Preflight hardware checks

Run at startup (non-fatal in development, strict in production mode if `AI_DEVICE_POLICY=gpu`).

- [ ] CPU path check:
  - confirm host RAM is above minimal threshold for selected model class.
- [ ] GPU path check:
  - detect GPU device,
  - detect free VRAM,
  - compare against `AI_MIN_FREE_VRAM_GB`.
- [ ] Emit clear startup status: `GPU_READY`, `GPU_DEGRADED`, or `CPU_ONLY`.

**Done when:** startup prints a single clear readiness state.

## Phase 3 — Hugging Face GPU execution

- [ ] Route model load/inference to CUDA/accelerator when policy resolves to GPU.
- [ ] Keep CPU fallback when preflight fails.
- [ ] Ensure cache/download behavior still uses:
  - `AI_HUGGINGFACE_CACHE_DIR`
  - `AI_HUGGINGFACE_ALLOW_DOWNLOAD`

**Done when:** same model can run on CPU or GPU via config-only switch.

## Phase 4 — Ollama GPU verification path

- [ ] Confirm `AI_OLLAMA_ENDPOINT` and `AI_OLLAMA_MODEL` path works with host Ollama GPU runtime.
- [ ] Add a health/info endpoint note in logs showing provider + device mode.
- [ ] Keep timeout guard via `AI_TIMEOUT_SECONDS`.

**Done when:** Ollama calls succeed and logs show whether GPU-backed runtime is active.

## Phase 5 — Runtime selection matrix (for routing)

Implement simple routing thresholds:

- [ ] Small models (<=1.5B): CPU allowed by default; GPU optional.
- [ ] Medium models (~3B): prefer GPU when available.
- [ ] Large models (7B+): require GPU or block selection with clear error.

**Done when:** selection logic rejects unsupported model/hardware combinations early.

## Phase 6 — Rollout + acceptance checks

- [ ] Add timing metrics around inference call (P50/P95).
- [ ] Track fallback count (GPU->CPU).
- [ ] Validate no regression in chat flow.

**Done when:**
- GPU path shows lower latency than CPU baseline for same prompt set.
- Error rate is stable.
- Fallback behavior is explicit and observable.

---

## Minimal preflight commands (operator quick checks)

### CPU-only baseline

```bash
lscpu
free -h
```

### NVIDIA GPU availability

```bash
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
```

### Optional live utilization sample

```bash
nvidia-smi dmon -s pucm -c 5
```

---

## Definition of done (project level)

- [ ] Config-driven device policy implemented.
- [ ] Startup preflight implemented and logged.
- [ ] HF provider supports GPU + CPU fallback.
- [ ] Ollama runtime path verified and logged.
- [ ] Model routing by size/hardware enforced.
- [ ] Latency + fallback metrics available.


---

## Local Transformers runtime (operator notes)

`ai_pipeline_v2` supports running Hugging Face models through `transformers` with either:

- a **repo ID** (for example `Qwen/Qwen2.5-3B-Instruct`), or
- a **local model directory** path.

### Required settings

- `AI_PROVIDER=huggingface`
- `AI_MODEL_NAME=<repo-id-or-local-path>`

### Cache location

- `AI_HUGGINGFACE_CACHE_DIR` controls where `from_pretrained(...)` reads/writes model artifacts.
- If set, this directory must be writable by the backend process.
- If omitted, transformers uses its default cache behavior.

### Online vs offline/local-only behavior

- `AI_HUGGINGFACE_ALLOW_DOWNLOAD=true`
  - repo IDs are allowed and missing artifacts can be downloaded into cache.
- `AI_HUGGINGFACE_ALLOW_DOWNLOAD=false`
  - backend runs in local-only mode and requires `AI_MODEL_NAME` to be an existing local model directory.

### Operational guidance

- Use repo IDs in environments with outbound network access and controlled cache volumes.
- Use local-only mode for air-gapped/offline deployments after pre-populating model files into cache/local path.
