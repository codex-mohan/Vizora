# AGENTS.md — Traffic Violation Detection System

Guidance for opencode agents working on this project. Read this before touching code.

## Project Context

Flipkart Gridlock 2.0 Hackathon — Round 2. Computer vision system that detects, classifies, and documents traffic violations from surveillance imagery. Full design lives in `PLAN.md` — read it first for architecture, model stack, violation logic, and edge cases.

## Repo Layout (target structure)

```
.
├── PLAN.md                  # authoritative design doc
├── AGENTS.md                # this file
├── backend/                 # Python CV pipeline + API
│   ├── api/                 # FastAPI routes
│   ├── pipeline/            # preprocessing, detection, tracking, violation logic, anpr, vlm
│   ├── models/              # model weights + configs (gitignored)
│   ├── core/                # state machine, queue, config
│   └── tests/
├── frontend/                # Next.js dashboard
│   ├── app/                 # App Router pages
│   ├── components/          # shadcn/ui + custom
│   └── lib/                 # API client, types
├── data/                    # sample images, annotations (gitignored large files)
├── docker/                  # Dockerfiles per service
└── docker-compose.yml
```

## Tech Stack

**Backend (Python):**
- Detection: configurable via Pydantic model registry (YOLO11 for MVP, RT-DETRv2 for accuracy, D-FINE for review)
- Tracking: ByteTrack v2
- Pose: RTMO-m
- Helmet: YOLO11 detection-style detector (no crop classifiers)
- Seatbelt: YOLO11 detection-style detector (no crop classifiers)
- ANPR: YOLOv11-plate + PaddleOCR PP-OCRv5 (primary), PARSeq (review)
- VLM: configurable via Pydantic model registry (Qwen-VL preferred, Florence-2 fallback)
- Preprocessing: OpenCV + Zero-DCE++ + AOD-Net + NAFNet + DerainNet
- Serving: FastAPI + TensorRT FP16
- Queue: Redis
- Storage: PostgreSQL + MinIO/S3

**Frontend:**
- Next.js 14 (App Router) + TypeScript
- Tailwind + shadcn/ui
- Tremor Raw (copy-paste chart components over recharts), react-map-gl + MapLibre GL (vector maps)

## Critical Design Decisions (do not violate)

1. **Preprocessing is camera-level state machine, NOT per-frame switching.** See PLAN.md §5. A camera has a sticky MODE (CLEAN/LOWLIGHT/HAZE/RAIN/MULTI) re-evaluated every ~5s via EWMA + weather API + sun position. Per-frame switching causes tracking flicker. Never implement per-frame conditional preprocessing.

2. **Tracking input must be temporally consistent.** Don't toggle enhancement models on/off between frames of the same camera. Mode changes are sticky (30+ good evals to exit DEGRADED).

3. **Hard 15 ms preprocessing budget per frame.** If a Tier 2 model would overflow, drop it and log — don't let latency vary. Deterministic timing keeps ByteTrack stable.

4. **5 of 7 violations are temporal.** Triple-ride, wrong-side, stop-line, red-light, illegal-parking need track trajectory across frames. Helmet and seatbelt are single-frame OK. For still-image input, degrade gracefully with lower confidence + review queue.

4a. **The system is image-first.** The hackathon theme is automated photo identification. Upload/single-image inference must work before temporal burst/video enhancements. Do not make ByteTrack mandatory for the still-image path.

4b. **Realtime is the deployability differentiator.** The product must expose a realtime/near-realtime feed path (SSE is acceptable for prototype) so the demo proves live surveillance scalability, not only offline upload.

5. **OCR pipeline is two-stage.** PaddleOCR primary (≥0.7 accept) → Real-ESRGAN super-res on crop + PARSeq for <0.7 → human review for still-low. The VLM is NOT the OCR authority — it's the violation-description module only.

6. **Privacy-by-design.** Face blur + plate redaction in public-facing copies. Store plate-hash for lookup. DPDP Act compliance.

7. **Evidence packets are tamper-evident.** SHA-256 hash chain across frames + JSON metadata + VLM description.

## Model Selection Rationale (don't second-guess without reason)

- **Detector is profile-based:** YOLO11 for MVP speed/tooling; RT-DETRv2 for accuracy; D-FINE for review profile.
- **ByteTrack v2 over OC-SORT/BoT-SORT:** highest IDF1 (fewest ID switches), associates low-confidence detections (occluded vehicles), no Re-ID needed.
- **RTMO-m over RTMPose:** multi-person single-stage, no separate person crop, handles triple-ride in one pass.
- **Helmet/headwear:** no EfficientNet crop classifier, no redundant backup. Use detection-style YOLO only.
- **Seatbelt:** YOLO detection-style detector (Safe-Drive-TN). No crop classifiers.
- **ANPR is reactive:** only runs when violations are detected, not on every frame. Saves GPU/CPU cycles.
- **PaddleOCR over PARSeq as primary:** Indian regional-language plates (Hindi/Tamil/Bengal) handled natively; PARSeq is English-only without per-language fine-tuning. PARSeq wins on dirty/stylized → use as review fallback.
- **Qwen-VL as preferred VLM:** stronger evidence descriptions when deployment target supports it; Florence-2 remains lightweight fallback. VLM output is explanation only, never final violation authority.

## Model Configuration Rules

- Model choices must be declared in `backend/core/model_registry.py` as Pydantic enums/schemas.
- Pipeline code must read selected models from the registry/profile. Do not hardcode model names inside detector/OCR/VLM modules.
- Startup must fail fast if an unsupported model choice appears in config.
- Add new model choices by extending the enum + schema first, then implementation adapter.

## Commands

**Full app (from repo root):**
- `pnpm dev` — run backend + frontend concurrently
- `pnpm test:e2e` — run Vitest E2E tests

Backend (run from `backend/`):
- `uv venv && uv pip install -e .` — create venv + install package in editable mode
- `uv add <package>` — add a dependency (writes pyproject.toml/lockfile, never edit manually)
- `uv sync` — sync env from lockfile
- `uv run uvicorn api.main:app --reload` — run API dev server
- `uv run pytest tests/` — run tests
- `uv run python -m pipeline.infer --input <path>` — run pipeline on sample

Frontend (run from `frontend/`):
- Scaffolded via `npx create-next-app@latest` + `npx shadcn@latest init` (never manual package.json/component config)
- `pnpm install` — install deps
- `pnpm dev` — dev server
- `pnpm build` — production build
- `pnpm lint` — eslint
- `pnpm typecheck` — tsc --noEmit
- `pnpm dlx shadcn@latest add <component>` — add a shadcn component

Before committing backend changes, run lint/typecheck if available. Always run `pnpm lint` and `pnpm typecheck` after frontend changes.

## Tooling Rules

- **Python:** use `uv` for all package management. Never hand-write `requirements.txt` or `pyproject.toml` dependency lists — use `uv add`. The `pyproject.toml` is generated/managed by uv.
- **Frontend:** use `create-next-app` and `shadcn` CLI for scaffolding. Never hand-write `package.json` deps or shadcn component files — use `npx shadcn@latest add`.
- **Latest libraries:** prefer latest stable versions (let uv/pnpm resolve). Pin only if a known incompatibility exists.

## Conventions

- Python: type hints, PEP 8, functions documented with docstrings where non-obvious. NO comments unless logic is genuinely non-obvious.
- Frontend: TypeScript strict, shadcn/ui components, server components by default, client components only for interactivity.
- Don't add Streamlit. Dashboard is Next.js. Period.
- Don't add comments to code unless asked.
- Never commit model weights or large datasets — they're gitignored.

## Dashboard Scope (rational — do not over-build)

The dashboard is the human-facing proof/review/analytics layer, NOT an admin panel. Three audiences: enforcement reviewer, analyst, hackathon judge.

Must-have pages (see PLAN.md §10.2 for detail):
1. **Upload / Process** — upload image/batch/short clip, run inference, show annotated result and evidence packet
2. **Overview** — KPIs + real-time violation feed (SSE) + mini hotspot map + type donut
3. **Violations** — searchable/filterable data table → row click opens evidence viewer
4. **Evidence Viewer** — annotated frame gallery + plate crop + OCR result + VLM description + hash-chain badge + approve/reject/escalate actions + face-blur/plate-redaction
5. **Analytics** — time-of-day trend, hotspot heatmap, repeat-offender table, type distribution
6. **Cameras** — camera list with current preprocessing MODE + status (demos the state machine)
7. **Review Queue** — low-confidence violations, human-in-loop workflow

Do NOT build: user auth, model-config UI, fine-tuning UI, real camera video streaming (use sample media for demo), admin settings panel.

## Edge Cases to Handle (see PLAN.md §11 for full list)

Key ones agents must not break:
- Turban/pagdi rider → NOT a helmet violation
- Emergency vehicles (ambulance/fire) → exempt from red-light/stop-line
- Child on lap → triple-ride nuance, not automatic violation
- Vehicle already past stop-line when signal turned red → not a violation
- Duplicate violation same vehicle/camera within 60s → cooldown, single record

## Open Items (resolve before/as we build)

- Indian regional-language plate dataset availability
- Emergency-vehicle exemption: signal/siren detector vs manual zone config
- Demo deployment target: local GPU vs hackathon cloud
