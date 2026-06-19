# Graph Report - Gridlock Hackathon 2.0 Round 2  (2026-06-19)

## Corpus Check
- 72 files · ~402,995 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 293 nodes · 537 edges · 14 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]

## God Nodes (most connected - your core abstractions)
1. `InferencePipeline` - 19 edges
2. `ViolationEngine` - 19 edges
3. `AnprPipeline` - 18 edges
4. `BBox` - 16 edges
5. `Image-first inference orchestrator.` - 16 edges
6. `TrackerAdapter` - 16 edges
7. `DetectedObject` - 15 edges
8. `BinaryClassifierAdapter` - 15 edges
9. `DetectorAdapter` - 15 edges
10. `PoseEstimatorAdapter` - 14 edges

## Surprising Connections (you probably didn't know these)
- `_Signal` --uses--> `Settings`  [INFERRED]
  backend\core\camera_state.py → backend\core\config.py
- `FrameQuality` --uses--> `CameraMode`  [INFERRED]
  backend\core\camera_state.py → backend\core\config.py
- `CameraState` --uses--> `CameraMode`  [INFERRED]
  backend\core\camera_state.py → backend\core\config.py
- `CameraStateRegistry` --uses--> `CameraMode`  [INFERRED]
  backend\core\camera_state.py → backend\core\config.py
- `Camera-level preprocessing state machine.  See PLAN.md §5. A camera has a sticky` --uses--> `Settings`  [INFERRED]
  backend\core\camera_state.py → backend\core\config.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (29): Camera-level preprocessing state machine.  See PLAN.md §5. A camera has a sticky, _Signal, CameraMode, Central configuration for the traffic violation detection pipeline., ClassifierChoice, ClassifierConfig, ComponentConfig, DetectorChoice (+21 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (18): BaseSettings, CameraState, CameraStateRegistry, FrameQuality, Settings, ModelProfile, EvidencePacket, EvidencePacketBuilder (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (16): AnprPipeline, build_anpr_pipeline(), ANPR adapter boundary., Helmet and seatbelt classifier adapter boundary., OcrConfig, Detection adapter boundary., BBox, DetectedObject (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.21
Nodes (9): ProcessingMode, ReviewReason, Track, ViolationPrediction, build_tracker(), Tracking adapter boundary., TrackerAdapter, Rule engine for image-first and temporal traffic violations. (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (13): BaseModel, ModelProfiles, Point, CameraSceneConfig, default_scene_config(), LaneDirection, load_scene_config(), PolygonZone (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (3): BinaryClassifierAdapter, build_helmet_classifier(), build_seatbelt_classifier()

### Community 7 - "Community 7"
Cohesion: 0.33
Nodes (2): build_detector(), DetectorAdapter

### Community 8 - "Community 8"
Cohesion: 0.36
Nodes (2): build_vlm_describer(), VlmDescriber

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (2): In-memory realtime event bus for prototype SSE feeds., RealtimeEventBus

### Community 11 - "Community 11"
Cohesion: 0.48
Nodes (4): chain_hash(), Tamper-evident hash-chain helpers for evidence packets., sha256_bytes(), sha256_json()

### Community 12 - "Community 12"
Cohesion: 0.29
Nodes (2): processMedia(), submit()

### Community 15 - "Community 15"
Cohesion: 0.5
Nodes (2): isHealthy(), waitForBackend()

### Community 16 - "Community 16"
Cohesion: 0.5
Nodes (3): lifespan(), FastAPI application entry point., load_model_profiles()

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (2): cn(), Badge()

## Knowledge Gaps
- **6 isolated node(s):** `FastAPI application entry point.`, `Central configuration for the traffic violation detection pipeline.`, `Pydantic-validated model registry.  All model choices live here so pipeline modu`, `In-memory realtime event bus for prototype SSE feeds.`, `Shared pipeline data contracts.` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 7`** (9 nodes): `detector.py`, `build_detector()`, `DetectorAdapter`, `._boxes_overlap()`, `.detect()`, `._infer_riders()`, `.__init__()`, `._load_model()`, `ready()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 8`** (9 nodes): `describer.py`, `build_vlm_describer()`, `ready()`, `VlmDescriber`, `._build_prompt()`, `._call_external_api()`, `.describe()`, `.__init__()`, `._template_description()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (7 nodes): `realtime.py`, `In-memory realtime event bus for prototype SSE feeds.`, `RealtimeEventBus`, `._format_sse()`, `.__init__()`, `.publish()`, `.subscribe()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (7 nodes): `page.tsx`, `api.ts`, `processMedia()`, `realtimeEventsUrl()`, `confidence()`, `handleFileChange()`, `submit()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (5 nodes): `demoPng()`, `isHealthy()`, `startBackend()`, `waitForBackend()`, `process-api.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (4 nodes): `badge.tsx`, `utils.ts`, `cn()`, `Badge()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InferencePipeline` connect `Community 1` to `Community 2`, `Community 3`, `Community 5`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `Image-first inference orchestrator.` connect `Community 1` to `Community 2`, `Community 3`, `Community 5`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `VlmDescriber` connect `Community 8` to `Community 0`, `Community 1`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `str` (e.g. with `.recognize()` and `._load_model()`) actually correct?**
  _`str` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `InferencePipeline` (e.g. with `CameraStateRegistry` and `Settings`) actually correct?**
  _`InferencePipeline` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ViolationEngine` (e.g. with `InferencePipeline` and `Image-first inference orchestrator.`) actually correct?**
  _`ViolationEngine` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `FastAPI application entry point.`, `Central configuration for the traffic violation detection pipeline.`, `Pydantic-validated model registry.  All model choices live here so pipeline modu` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._