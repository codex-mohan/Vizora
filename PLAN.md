# PLAN.md — Automated Traffic Violation Detection System

Flipkart Gridlock 2.0 Hackathon — Round 2
Computer Vision–based traffic violation identification, classification, and evidence generation.

---

## 1. Problem Statement

Traffic surveillance cameras generate millions of images daily. Manual review is slow, inconsistent, and unscalable. We need an end-to-end CV pipeline that ingests raw traffic images (or short video bursts), detects road users, identifies and classifies violations, reads license plates, and produces court-admissible annotated evidence — robust to weather, lighting, density, and image quality, and scalable to city-wide deployment.

---

## 2. Goals & Deliverables

### 2.1 Functional Goals
- Support photo upload/batch processing as the baseline challenge requirement
- Support realtime/near-realtime processing feed as the deployability differentiator
- Detect and localize vehicles, riders, drivers, pedestrians
- Detect 7 violation types: helmet, seatbelt, triple-ride, wrong-side, stop-line, red-light, illegal parking
- Classify each violation with confidence score
- ANPR: detect plates + extract registration via OCR
- Generate annotated, tamper-evident evidence packets
- Analytics dashboard: hotspots, trends, searchable records
- Natural-language violation description via VLM

### 2.2 Non-Functional Goals
- Robust to night, rain, fog, glare, motion blur, occlusion, dense traffic
- Scalable: microservices, async queue, horizontal GPU scaling
- Privacy-by-design: face blurring, plate redaction, DPDP-compliant
- Accurate: calibrated confidence, human-in-loop fallback

### 2.3 Deliverables
- Working prototype (FastAPI backend + Next.js dashboard)
- Sample annotated evidence packets (images + JSON + VLM description)
- Evaluation metrics report (P/R/F1/mAP/latency)
- Architecture diagram + deployment guide
- Edge-case test set with documented handling
- Pitch deck

---

## 3. System Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Ingestion   │───▶│ Preprocessing│───▶│  Detection + │───▶│  Violation      │
│  (RTSP/API/  │    │  (Tiered:    │    │  Tracking    │    │  Reasoning      │
│   batch)     │    │  classical + │    │  (registry + │    │  (rule + pose + │
└──────────────┘    │  lightweight)│    │  ByteTrack)  │    │  classifiers)   │
                    └──────────────┘    └──────────────┘    └────────┬────────┘
                                                                       │
                                                          ┌────────────┴───────────┐
                                                          ▼                        ▼
                                                 ┌────────────────┐      ┌────────────────┐
                                                 │  ANPR          │      │  VLM Violation │
                                                 │  (YOLO-plate + │      │  Description   │
                                                 │   PaddleOCR)   │      │  (Qwen-VL)     │
                                                 └───────┬────────┘      └────────┬───────┘
                                                         │                        │
                                                         ▼                        ▼
                                                 ┌──────────────────────────────────────┐
                                                 │  Evidence Generation + Metadata Store │
                                                 │  (annotated frames + hash-chain JSON) │
                                                 └──────────────────┬───────────────────┘
                                                                    ▼
                                                 ┌──────────────────────────────────────┐
                                                 │  Analytics & Reporting (Next.js +     │
                                                 │  Postgres + MapLibre)                 │
                                                 └──────────────────────────────────────┘
```

---

## 4. Configurable Model Stack

The stack must be configurable, not hardcoded. Every model is selected through a **Pydantic-validated model registry** so we can switch between MVP, accuracy, edge, and review profiles without changing pipeline code.

### 4.1 Model registry rule

Pipeline code never imports a model implementation directly. It asks the model registry for the configured component:

```
model_profile.yaml → Pydantic validation → ModelRegistry → pipeline component
```

If a model name is not one of the allowed choices, startup fails fast with a clear validation error.

### 4.2 Supported choices

| Stage | Default | Other choices | Role |
|-------|---------|---------------|------|
| Detection | **YOLO11** for MVP | D-FINE-L for accuracy profile | Vehicle/rider/pedestrian detection |
| Tracking | **ByteTrack v2** | disabled for still-image mode | Track IDs for temporal violations |
| Pose | **RTMO-m** | disabled if not needed | Rider/person keypoints |
| Helmet classifier | **EfficientNetV2-S** | ConvNeXt-V2 for offline review | Helmet/no-helmet on rider head ROI |
| Seatbelt classifier | **EfficientNetV2-S** | ConvNeXt-V2 for offline review | Belt/no-belt on driver ROI |
| Plate detector | **YOLO11-plate** | custom detector later | Localize number plates |
| Plate OCR | **PaddleOCR PP-OCRv5** | PARSeq fallback | Extract registration text |
| VLM description | **Qwen-VL profile** | Florence-2 fallback | Natural-language evidence description |
| Preprocessing | **classical + quality scoring** | Zero-DCE++ optional | Normalize image quality |

### 4.3 Profiles

| Profile | Purpose | Detector | VLM | Preprocessing |
|---------|---------|----------|-----|---------------|
| `mvp` | fastest working deployable prototype | YOLO11 | Qwen-VL small/local or disabled | classical only |
| `accuracy` | stronger final demo | D-FINE-L | Qwen-VL larger profile | classical + optional Zero-DCE++ |
| `edge` | low-resource deployment | YOLO11n/s | disabled or tiny VLM remote | classical only |
| `review` | offline low-confidence review | D-FINE-L/YOLO11x | strongest available Qwen-VL | crop-level enhancement |

### 4.4 VLM policy

Qwen-VL is preferred for detailed violation descriptions when available because stronger visual reasoning helps produce clearer evidence narratives. Florence-2 remains a lightweight fallback. The VLM **must not decide violations**; it only writes a description from annotated frames and structured metadata produced by the deterministic pipeline.

Because exact Qwen 3.5 VLM specs must be verified from official sources before claims, the registry supports a `qwen3_5_vl` choice without hardcoding unverified latency/accuracy numbers.

---

## 5. Preprocessing — Camera-Level State Machine (Production-Grade)

### 5.1 Why NOT naive per-frame tiered switching

A naive "compute quality score per frame → conditionally run Tier 2" design breaks in production:

1. **Temporal flicker** — a passing cloud toggles Zero-DCE++ on/off across consecutive frames. The same vehicle looks different → ByteTrack appearance features mismatch → ID switches → triple-ride / wrong-side logic fails. This is the #1 killer.
2. **Unreliable quality scoring** — brightness metric says "fine" but a shadow covers the rider's head → helmet check fails. Rain detector false-triggers on headlight reflections → DerainNet runs needlessly.
3. **Non-deterministic latency** — clean frame 5 ms, degraded frame 40 ms. Variable timing → frame drops → track gaps.

### 5.2 The fix — camera-level state, not frame-level

Real systems maintain a **per-camera mode** (not per-frame decision). All frames from a camera use the same preprocessing mode until the camera's state changes.

```
Per CAMERA (not per frame):
  - Maintain rolling quality state (EWMA over last 30 frames)
  - Decide preprocessing MODE once per camera, re-evaluate every ~5s
  - All frames from that camera use the SAME mode until state changes

Per FRAME:
  - Run whatever mode the camera is currently in
  - NO per-frame switching decision
```

### 5.3 Camera state machine

```
  CLEAN ──(quality bad for 5+ consecutive evals)──▶ DEGRADED
     ▲                                                    │
     └───(quality good for 30+ consecutive evals)────────┘

MODES:
  CLEAN      → Tier 1 only
  LOWLIGHT   → Tier 1 + Zero-DCE++
  HAZE       → Tier 1 + AOD-Net
  RAIN       → Tier 1 + DerainNet
  MULTI      → Tier 1 + Zero-DCE++ + DerainNet  (e.g. night rain)
```

**Key invariant:** once a camera enters DEGRADED, it STAYS degraded even if a few frames look clean. Only exits after sustained good quality (30+ evals). This eliminates flicker — tracking sees consistent input.

### 5.4 Mode decision — 3 fused signals (not scorer alone)

Don't trust frame metrics alone. Fuse 3 signals; switch mode if 2 of 3 agree:

1. **Frame metrics (EWMA over 30 frames)** — brightness (mean HSV V), blur (Laplacian variance), haze (dark-channel prior), noise (local std). Cheap but noisy.
2. **Weather API** (camera lat/long → OpenWeather, 1 call/min) — authoritative for rain/fog.
3. **Time of day + sun position** (astronomy calc) — authoritative for low-light transitions.

Example: frame metric says "dark" but it's 2 PM and clear → ignore (shadow). Weather API says "heavy rain" → force DEGRADED regardless of frame metric.

### 5.5 Tier 1 — Always-on (classical, <2 ms, every frame, every mode)
- Lens undistortion (camera calibration matrix)
- ROI masking (crop road area, ignore sky/buildings)
- CLAHE (contrast)
- Gamma correction
- White balance
- HSV V-channel shadow removal
- Resize/letterbox to model input
- ImageNet mean/std normalization
- Tensor conversion + batch padding

### 5.6 Tier 2 — Mode-dependent lightweight deep models
Run persistently (not flickering) while camera is in the matching DEGRADED mode.

| Model | Mode trigger | Cost |
|-------|--------------|------|
| Zero-DCE++ | LOWLIGHT (brightness EWMA < threshold) | ~10 ms |
| AOD-Net | HAZE (dark-channel prior > threshold) | ~8 ms |
| DerainNet | RAIN (weather API or streak detector) | ~12 ms |
| NAFNet (small) | noise EWMA > threshold (sensor/JPEG) | ~30 ms |

### 5.7 Latency budget — fixed cap (deterministic)
- Hard **15 ms budget** per frame for preprocessing.
- CLEAN mode: 2 ms used, 13 ms idle.
- DEGRADED mode: Zero-DCE++ (10 ms) fits; if NAFNet (30 ms) would overflow → drop the heavy model, accept lower quality, log it.
- Tracking sees consistent ~15 ms timing → no frame drops, deterministic throughput.
- (Alternative for accuracy over speed: adaptive frame-skipping — process every 2nd frame in MULTI mode, tracker interpolates. Not used for hackathon demo.)

### 5.8 Tier 3 — On-demand (heavy, crops + review queue only)
Never on full-frame real-time path.

| Model | Applied to | When |
|-------|-----------|------|
| Real-ESRGAN | Plate crops only | plate OCR confidence < 0.6 on first pass |
| SRN-Deblur | Flagged frames only | human-review queue |

### 5.9 Known failure modes (honest)
- **Localized degradation** — shadow on half frame, sun on other. Camera-level mode can't be both. Fix: quadrant ROI scoring (added complexity, skip for hackathon).
- **Sudden flash/strobe** — lightning, police strobe. EWMA too slow. Fix: hard cap on inter-frame brightness delta → force single-frame DEGRADED + flag review. Rare.
- **Camera malfunction** — sensor noise spike misread as haze. Fix: ops alert, route camera to maintenance queue.

### 5.10 Net effect
Real-time path stays deterministic ~15 ms preprocess + ~30+ FPS pipeline. Heavy models only touch small crops or flagged frames. Tracking input is temporally consistent per camera.

---

## 6. Violation Detection Logic

### 6.0 Processing modes

The challenge is photo-first, so the prototype must work on single uploaded images. Temporal tracking is an enhancement for short clips/bursts, not a hard requirement for every input.

| Mode | Input | What it can prove confidently |
|------|-------|-------------------------------|
| Still-image mode | single image / batch of images | helmet, visible triple riding, plate OCR, visible stop-line overlap, visible parking in restricted zone if zone config exists |
| Realtime / temporal burst mode | live camera feed / short clip / frame sequence | wrong-side trajectory, red-light crossing, stop-line crossing at signal phase, illegal parking duration, stable triple-ride confirmation, live dashboard feed |

Temporal violations from still images receive lower confidence and may be routed to review unless camera scene metadata makes the evidence clear. Realtime mode is a first-class demo path, not a later add-on, because it proves the solution can scale from photo evidence to deployed surveillance workflows.

| Violation | Method | Temporal? |
|-----------|--------|-----------|
| Helmet non-compliance | RTMO pose + EfficientNetV2-S on head ROI | No (single frame ok) |
| Seatbelt non-compliance | Crop driver window ROI → EfficientNetV2-S classifier | No |
| Triple riding | Count persons on 2-wheeler track ID (ByteTrack) | Yes (track-stable) |
| Wrong-side driving | Track trajectory vector vs lane orientation vector | Yes |
| Stop-line violation | Homography → stop-line; vehicle box crosses while signal red | Yes |
| Red-light violation | Track crosses stop-line during red phase | Yes |
| Illegal parking | Stationary track > N seconds in no-parking polygon | Yes |

Key insight: 5 of 7 violations are temporal. We process short video bursts (5–10s) around trigger events. For pure still-image inputs, we degrade gracefully and flag lower confidence + route to review.

### 6.1 Camera scene configuration

Models alone cannot reliably infer traffic-law context. Each deployed camera needs a small scene config:

- Stop-line polygon
- Lane direction vectors
- No-parking zone polygons
- Signal-light ROI or external signal phase metadata
- Camera GPS/location
- Optional homography points for road-plane projection

Without this config, red-light, stop-line, wrong-side, and illegal-parking outputs must be marked as low-confidence or review-required.

### Confidence fusion
Each violation emits:
```
{
  class, confidence, bbox, track_id,
  detector_score, rule_logic_score, pose_score,
  supporting_evidence_frames[],
  timestamp, camera_id
}
```
Confidence = weighted fusion. Platt-scaled calibration for court defensibility.

---

## 7. ANPR Pipeline

```
Frame → YOLOv11-plate (detect)
         │
         ▼
       Plate crop
         │
         ▼
   PaddleOCR PP-OCRv5 (recognize)
         │
   ┌─────┴─────┐
   ▼           ▼
 conf≥0.7   conf<0.7
   │           │
 accept    Real-ESRGAN (Tier 3 super-res on crop)
              │
              ▼
           PARSeq (review)
              │
         ┌────┴────┐
         ▼         ▼
     conf≥0.7   conf<0.7
         │         │
      accept   human review queue
```
Post-process: Indian plate regex `XX 00 XX 0000`, fuzzy match RC DB if available, store plate + plate-hash.

---

## 8. VLM Violation Description Module (Configurable Qwen-VL / Florence Fallback)

### 8.1 Role
Generates a natural-language, court-readable violation description per evidence packet. Runs OFFLINE (not in real-time path), once per confirmed violation. The selected VLM comes from the Pydantic model registry.

### 8.2 Input
Annotated evidence frame(s) + structured JSON metadata:
```
{
  violation_type, confidence, vehicle_class, plate,
  location, timestamp, camera_id, speed_estimate, weather
}
```

### 8.3 Output example
> "On 2026-06-18 at 17:42:11 IST, camera BLR-CAM-014 (MG Road, Bengaluru) detected a black motorcycle (plate KA-01-AB-1234) with two male riders, neither wearing helmets. The rider executed a red-light violation by crossing the stop-line during signal phase RED. Detection confidence 0.94. Three supporting frames captured over 2.1s."

### 8.4 Preferred VLM choices

| Choice | Use |
|--------|-----|
| `qwen3_5_vl` | Preferred if official weights/API and deployment target are confirmed |
| `qwen2_5_vl_3b` | Practical local/default profile when GPU is limited |
| `qwen2_5_vl_7b` | Stronger review/accuracy profile when VRAM allows |
| `florence2_large` | Lightweight fallback if Qwen-VL cannot be deployed |
| `florence2_base` | Smallest fallback; description quality is weaker |

The VLM receives annotated images plus structured metadata and must produce explanation only. It must not override violation class, OCR, or confidence produced by the pipeline.

### 8.5 Invocation
Triggered after violation confirmed + evidence packet assembled. Async worker pulls from `evidence_queue`, calls the configured VLM, appends `description` field to stored record.

---

## 9. Evidence Generation

### 9.1 Evidence packet per violation
- 3–5 annotated frames (bbox, label, confidence, timestamp, camera ID, GPS)
- 1 short clip (temporal violations only)
- JSON metadata
- VLM natural-language description
- SHA-256 hash chain across packet (tamper-evidence)

### 9.2 Annotation
- Bounding boxes + violation label + confidence
- Plate redacted in public-facing copies, full plate in sealed evidence copy
- Face blur applied (DPDP compliance)
- Timestamp + camera ID + GPS watermark

---

## 10. Analytics & Reporting

### 10.1 Storage
- PostgreSQL: `violations`, `vehicles`, `cameras`, `locations`, `evidence_packets`
- Partitioned by region + month
- Object store (S3/MinIO) for images/clips

### 10.2 Dashboard (Next.js + shadcn/ui)

**Role:** Human-facing proof, review, and analytics layer. Backend does detection; UI makes results usable, verifiable, and demo-able. Three audiences: enforcement reviewer, analyst/supervisor, hackathon judge.

**Stack:** Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + Tremor Raw (copy-paste chart components, uses recharts) + react-map-gl + MapLibre GL (vector tiles from OpenFreeMap, road-level detail, dark mode, no API key). Fonts: Geist (Vercel).

**Pages & features (rational scope — no auth, no model-config UI, no fine-tuning UI):**

1. **Upload / Process (`/process`)**
   - Upload a traffic image, batch of images, or optional short clip
   - Select camera scene config (or use default demo config)
   - Run inference and show annotated output immediately
   - Show detected objects, violation classes, confidence scores, plate OCR, metadata, and evidence packet link
   - Purpose: direct demonstration of the hackathon task

2. **Overview (`/`)**
   - KPI cards: violations today, active cameras, review-queue depth, avg confidence
   - Real-time violation feed (Server-Sent Events) — latest 10 detections streaming in
   - Mini hotspot map
   - Violation-type donut chart
   - Purpose: instant "system is alive and working" impression

3. **Violations (`/violations`)**
   - Data table (shadcn): timestamp, type, camera, location, plate, confidence, status
   - Filters: type, date range, camera, confidence range, plate search, review-required toggle
   - Pagination + sort
   - Row click → evidence viewer
   - Purpose: searchable record book

4. **Evidence Viewer (`/evidence/[id]`)**
   - Annotated image gallery (3–5 frames) with bbox + label + confidence overlays
   - Side panel: violation metadata (type, confidence, timestamp, camera, GPS, vehicle class)
   - Plate crop + OCR result + OCR confidence
   - VLM natural-language violation description
   - SHA-256 hash-chain verification badge (tamper-evident)
   - Privacy: faces blurred, plate-redaction toggle (public vs sealed view)
   - Review actions: approve / reject / escalate (human-in-loop)
   - Purpose: court-admissible proof packet + review workflow

5. **Analytics (`/analytics`)**
   - Time-of-day trend (Tremor area chart)
   - Violation-type distribution (Tremor donut/bar)
   - Hotspot map (MapLibre GL, circle markers at camera GPS coords sized by violation count, road-level zoom)
   - Repeat-offender table (by plate-hash, count, last-seen)
   - Day-of-week × hour heatmap
   - Purpose: trend analysis, resource planning

6. **Cameras (`/cameras`)**
   - Camera list: status (online/offline), current preprocessing MODE (CLEAN/LOWLIGHT/HAZE/RAIN/MULTI), location, throughput
   - Camera detail: live mode-timeline, quality-metrics graph (brightness/haze/noise EWMA)
   - Purpose: system health + visual demo of the preprocessing state machine

7. **Review Queue (`/violations?review=1`)**
   - Low-confidence violations (< threshold) or edge-case flags
   - Same evidence viewer, with approve/reject workflow front and center
   - Purpose: human-in-loop fallback (graceful degradation)

**Frontend tooling:** Scaffolded via `create-next-app` + `shadcn init` CLI (never manual package config). TypeScript strict. Server components by default; client components only for interactivity (maps, charts, SSE feed, filters).

---

## 11. Edge Cases (must handle)

### 11.1 Environmental
- Night/low-light, heavy rain, fog, dust
- Lens flare, direct sunlight glare
- Shadows mimicking vehicles/lines
- Wet-road reflections
- Motion blur, camera shake
- Rain droplets on lens

### 11.2 Traffic / Scene
- Heavy occlusion (bus blocking car behind)
- Dense traffic, vehicles cut mid-frame
- Two-wheelers overlapping (triple-ride false positives)
- Non-standard vehicles: e-rickshaw, bullock cart, tractor, cycle, wheelchair
- Pedestrians crossing at stop-line (not a violation)
- Emergency vehicles (ambulance/fire) — exempt from red-light/stop-line
- Funeral processions, VIP convoys with pilot vehicles

### 11.3 Plate / OCR
- Dirty/damaged plates, non-standard fonts
- Regional language plates, fancy plates
- Plate occluded by bike rack/tow hook
- Out-of-state, diplomatic, BH-series plates
- Reflection/glare on plate → route to review

### 11.4 Violation Logic
- Rider wearing turban/pagdi — do NOT flag helmet missing
- Helmet on but strap unbuckled (advanced, optional)
- Seatbelt hidden by dark clothing / hand on chest
- Child on lap (triple-ride vs child-safety nuance)
- Vehicle legally turning left on red (where permitted)
- Vehicle already past stop-line when signal turned red
- Parked vehicle in marked loading zone
- Emergency/funeral exemption logic

### 11.5 System / Pipeline
- Duplicate violation from same vehicle at same camera within 60s cooldown
- Camera offline / frame drops mid-tracking → track re-ID
- Clock drift → NTP sync requirement
- Adversarial: stickers/posters mimicking plates/signs
- Privacy: face blurring, plate redaction, DPDP Act compliance

---

## 12. Evaluation Plan

### 12.1 Detection
- mAP@0.5, mAP@0.5:0.95
- Per-class AP (car, bike, truck, bus, auto, rider, pedestrian)

### 12.2 Violation Classification
- Per-class Precision / Recall / F1
- Confusion matrix across 7 violation types
- Calibrated probability (Brier score)

### 12.3 ANPR
- Plate detection recall
- Character-level accuracy
- Full-plate exact-match accuracy

### 12.4 Performance
- p50 / p95 latency per frame
- Throughput (FPS) on A10 / T4 / Jetson Orin
- Concurrent streams per GPU
- Scalability test: simulate 50 concurrent camera streams

### 12.5 Robustness
- Accuracy stratified by: day/night, rain/clear, fog/clear, dense/sparse traffic
- Edge-case pass rate (turban, emergency vehicle, child-on-lap)

---

## 13. Scalability & Deployment

### 13.1 Architecture
- Microservices: each module independently containerized
- Async queue (Redis/RabbitMQ) decouples ingestion from processing
- GPU batching; dynamic frame batching
- Stateless workers → K8s autoscale on queue depth

### 13.2 Edge–Cloud Split
- Edge (Jetson Orin): Tier 1 preprocessing, selected detector profile, ByteTrack, plate detect
- Cloud (A10/A100): violation reasoning, ANPR OCR, configured VLM description, analytics

### 13.3 Target Capacity
- 1× A10: ~40 FPS pipeline → ~8 cameras at 5 FPS
- Linear horizontal scale
- Estimated city deployment: 1 GPU per 8 cameras

---

## 14. Tech Stack Summary

| Layer | Tech |
|-------|------|
| Detection | Model registry: YOLO11 for MVP, D-FINE-L for accuracy profile |
| Tracking | ByteTrack v2 |
| Pose | RTMO-m |
| Classifiers | EfficientNetV2-S |
| ANPR | YOLOv11-plate + PaddleOCR PP-OCRv5 + PARSeq (review) |
| VLM | Model registry: Qwen-VL preferred, Florence-2 fallback |
| Preprocessing | OpenCV + Zero-DCE++ + AOD-Net + NAFNet + DerainNet |
| Serving | FastAPI + TensorRT FP16 |
| Queue | Redis / RabbitMQ |
| Storage | PostgreSQL + MinIO/S3 |
| Dashboard | Next.js 14 + shadcn/ui + Tremor Raw + MapLibre GL |
| Python packaging | uv |
| Frontend packaging | pnpm |
| Deploy | Docker + Kubernetes |

---

## 15. Innovation / Differentiators

1. Temporal reasoning — ByteTrack + homography for true violation logic (not single-frame)
2. Court-admissible evidence — hash-chained packets, calibrated confidence, VLM description
3. India-specific edge cases — turban exemption, child-on-lap, emergency vehicles, regional plates
4. Tiered preprocessing — real-time path stays fast, heavy models only on crops/flagged frames
5. Human-in-loop fallback — graceful degradation, not binary pass/fail
6. VLM natural-language evidence — Qwen-VL/Fallback VLM makes records readable for non-technical reviewers
7. Privacy-by-design — face/plate redaction, DPDP-compliant

---

## 16. Milestones

| Milestone | Target |
|-----------|--------|
| Data collection + annotation (Indian plates, violations) | Week 1 |
| Detection + tracking pipeline | Week 1–2 |
| Preprocessing tiers + quality scoring | Week 2 |
| Violation logic (7 types) | Week 2–3 |
| ANPR pipeline + OCR | Week 3 |
| Evidence gen + VLM description | Week 3 |
| Analytics dashboard | Week 3–4 |
| Evaluation + optimization | Week 4 |
| Pitch deck + demo polish | Week 4 |

---

## 17. Open Questions

1. Indian regional-language plate dataset — available, or English-only?
2. VLM deployment target — local Qwen-VL, hosted Qwen-VL API, or Florence-2 fallback?
3. Emergency-vehicle exemption — do we have signal/siren detector, or manual zone config?
4. Deployment target — demo on local GPU, or cloud demo environment provided by hackathon?
