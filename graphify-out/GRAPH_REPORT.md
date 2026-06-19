# Graph Report - Gridlock Hackathon 2.0 Round 2  (2026-06-19)

## Corpus Check
- 100 files · ~420,109 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 597 nodes · 1452 edges · 20 communities detected
- Extraction: 51% EXTRACTED · 49% INFERRED · 0% AMBIGUOUS · INFERRED: 711 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 27|Community 27]]

## God Nodes (most connected - your core abstractions)
1. `BBox` - 62 edges
2. `ViolationEngine` - 57 edges
3. `Point` - 45 edges
4. `DetectedObject` - 36 edges
5. `ObjectClass` - 34 edges
6. `ViolationPrediction` - 32 edges
7. `ViolationClass` - 31 edges
8. `Track` - 26 edges
9. `ProcessingMode` - 25 edges
10. `EvidenceAnnotator` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Alembic async environment configuration.` --uses--> `Base`  [INFERRED]
  backend\alembic\env.py → backend\core\database.py
- `get_current_user()` --calls--> `decode_access_token()`  [INFERRED]
  backend\api\deps.py → backend\core\auth.py
- `FastAPI dependencies: authentication, current user, role checks.` --uses--> `User`  [INFERRED]
  backend\api\deps.py → backend\core\models\organization.py
- `Parsed current user from JWT.` --uses--> `User`  [INFERRED]
  backend\api\deps.py → backend\core\models\organization.py
- `Extract and validate current user from JWT token.` --uses--> `User`  [INFERRED]
  backend\api\deps.py → backend\core\models\organization.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (53): CurrentUser, get_current_user(), FastAPI dependencies: authentication, current user, role checks., Parsed current user from JWT., Extract and validate current user from JWT token., Dependency factory: require the current user to have one of the given roles., require_role(), Base (+45 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (25): ANPR adapter boundary., Helmet and seatbelt classifier adapter boundary., annotate_evidence(), EvidenceAnnotator, Evidence image annotator: draws bboxes, labels, face blur, plate redaction, wate, Take raw image bytes + inference result, return annotated PNG bytes., Draws annotated evidence images for violation packets., Return annotated copy of *image* with all overlays. (+17 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (38): Camera-level preprocessing state machine.  See PLAN.md §5. A camera has a sticky, _Signal, CameraMode, Central configuration for the traffic violation detection pipeline., ClassifierChoice, ClassifierConfig, ComponentConfig, DetectorChoice (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (31): PlateResult, Point, PoseResult, ProcessingMode, ReviewReason, Track, CameraSceneConfig, default_scene_config() (+23 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (21): BaseSettings, BinaryClassifierAdapter, build_helmet_classifier(), build_seatbelt_classifier(), CameraState, CameraStateRegistry, FrameQuality, Settings (+13 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (19): load(), handleSubmit(), load(), handleAction(), load(), apiFetch(), authHeaders(), createCamera() (+11 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (10): TestIsStationary, TestPointInPolygon, TestViolationCooldown, compute_trajectory_direction(), is_moving_against_lane(), is_stationary(), line_segment_intersects_polygon(), point_in_polygon() (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (17): EvidencePacket, Evidence packet generation., MediaInput, avg_latency(), BenchmarkResult, char_accuracy(), compute_iou(), evaluate_violations() (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (8): chain_hash(), Tamper-evident hash-chain helpers for evidence packets., sha256_bytes(), sha256_json(), Tests for evidence hash chain., TestChainHash, TestSha256Bytes, TestSha256Json

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (12): get_storage(), MinIO/S3 object storage client for evidence images and video clips., Wraps MinIO client for evidence storage., Create bucket if it doesn't exist., Upload image bytes, return object key., Upload video bytes, return object key., Download object by key, return bytes., Get presigned URL for direct client access. (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.17
Nodes (9): create_access_token(), decode_access_token(), hash_password(), JWT authentication and password hashing utilities., Decode JWT, return payload dict or None if invalid., verify_password(), Tests for authentication utilities., TestJWTToken (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.27
Nodes (3): build_detector(), DetectorAdapter, ready()

### Community 12 - "Community 12"
Cohesion: 0.31
Nodes (2): AnprPipeline, build_anpr_pipeline()

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (5): lifespan(), FastAPI application entry point., init_db(), Async SQLAlchemy engine, session factory, and FastAPI dependency., load_model_profiles()

### Community 16 - "Community 16"
Cohesion: 0.33
Nodes (2): In-memory realtime event bus for prototype SSE feeds., RealtimeEventBus

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (3): Alembic async environment configuration., run_async_migrations(), run_migrations_online()

### Community 20 - "Community 20"
Cohesion: 0.5
Nodes (2): isHealthy(), waitForBackend()

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (1): initial schema  Revision ID: 001 Revises: Create Date: 2026-06-18

### Community 22 - "Community 22"
Cohesion: 0.5
Nodes (2): cn(), Badge()

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Test configuration and compatibility fixes.

## Knowledge Gaps
- **23 isolated node(s):** `initial schema  Revision ID: 001 Revises: Create Date: 2026-06-18`, `FastAPI application entry point.`, `JWT authentication and password hashing utilities.`, `Decode JWT, return payload dict or None if invalid.`, `Central configuration for the traffic violation detection pipeline.` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (10 nodes): `AnprPipeline`, `._estimate_plate_region()`, `.__init__()`, `._load_ocr()`, `._normalize_text()`, `._offset_ocr_box()`, `.recognize()`, `build_anpr_pipeline()`, `ready()`, `pipeline.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (7 nodes): `realtime.py`, `In-memory realtime event bus for prototype SSE feeds.`, `RealtimeEventBus`, `._format_sse()`, `.__init__()`, `.publish()`, `.subscribe()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (5 nodes): `demoPng()`, `isHealthy()`, `startBackend()`, `waitForBackend()`, `process-api.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (4 nodes): `001_initial.py`, `downgrade()`, `initial schema  Revision ID: 001 Revises: Create Date: 2026-06-18`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (4 nodes): `badge.tsx`, `utils.ts`, `cn()`, `Badge()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `conftest.py`, `Test configuration and compatibility fixes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Persist inference results to database and MinIO.` connect `Community 0` to `Community 3`, `Community 4`, `Community 7`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `ViolationEngine` connect `Community 3` to `Community 1`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `InferencePipeline` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 7`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 60 inferred relationships involving `BBox` (e.g. with `AnprPipeline` and `ANPR adapter boundary.`) actually correct?**
  _`BBox` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `ViolationEngine` (e.g. with `InferencePipeline` and `Image-first inference orchestrator.`) actually correct?**
  _`ViolationEngine` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `Point` (e.g. with `PolygonZone` and `LaneDirection`) actually correct?**
  _`Point` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `str` (e.g. with `register()` and `login()`) actually correct?**
  _`str` has 20 INFERRED edges - model-reasoned connections that need verification._