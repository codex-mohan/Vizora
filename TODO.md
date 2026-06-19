# TODO — Vizora

## 1. Real Camera Feed Infrastructure
- [ ] RTSP stream ingestion (OpenCV VideoCapture / FFmpeg)
- [ ] Camera registration API (add/remove/update cameras with GPS, scene config, credentials)
- [ ] Per-camera preprocessing state machine (CLEAN/LOWLIGHT/HAZE/RAIN/MULTI) with EWMA
- [ ] Frame buffer + ring buffer for temporal burst processing
- [ ] ByteTrack integration on live frame stream (not just single image)
- [ ] Camera health monitoring (online/offline/fps/latency)
- [ ] Camera scene config editor (stop-line polygon, lane direction, no-parking zone, signal ROI)
- [ ] WebSocket/SSE push for live annotated frames to frontend
- [ ] Multi-camera concurrent processing (thread pool / async workers)
- [ ] Video recording + clip extraction for evidence packets
- [ ] Camera discovery / auto-detection on local network
- [ ] NTP time sync across cameras
- [ ] Graceful degradation when camera goes offline mid-stream

## 2. Landing Page Refinement
- [ ] Gather real traffic surveillance images for hero/feature sections (royalty-free or synthetic)
- [ ] Add animated detection overlay demo (auto-playing bbox animation on sample image)
- [ ] Add interactive model stack diagram (click to see each model's role)
- [ ] Add social proof section (datasets used, benchmark numbers, supported violation types)
- [ ] Add animated statistics counter (violations processed, cameras supported, accuracy)
- [ ] Add comparison table (Vizora vs manual review vs generic CV tools)
- [ ] Add FAQ section
- [ ] Add smooth scroll behavior for anchor links
- [ ] Add page transition animations between routes
- [ ] Add OG meta tags + favicon + social preview image
- [ ] Gather SVG illustrations for workflow steps (replace CSS mockups)
- [ ] Add dark/light theme toggle (dark default, light option)
- [ ] Add responsive mobile nav (hamburger menu)
- [ ] Add loading skeleton states for async widgets

## 3. Analytics Page Improvement
- [ ] Replace static sample data with real API calls to `/api/analytics/summary` and `/api/analytics/hotspots`
- [ ] Add Recharts area chart for time-of-day violation trend
- [ ] Add Recharts donut chart for violation type distribution
- [ ] Add MapLibre hotspot map with circle markers sized by violation count
- [ ] Add day-of-week × hour heatmap grid
- [ ] Add date range filter (date picker)
- [ ] Add camera filter (multi-select)
- [ ] Add violation type filter
- [ ] Add export to CSV button
- [ ] Add export to PDF report button
- [ ] Add repeat offender table with plate-hash, count, last-seen, violation types
- [ ] Add confidence distribution histogram
- [ ] Add model accuracy metrics panel (P/R/F1 per violation type)
- [ ] Add processing latency graph (p50/p95 over time)
- [ ] Add real-time update via SSE (new violations push to charts)

## 4. Missing Pages & Views
- [ ] **Evidence Viewer (`/evidence/[id]`)** — connect to real API, show annotated image with bbox overlays, plate crop, OCR result, VLM description, hash chain badge, approve/reject/escalate actions
- [ ] **Review Queue (`/review`)** — low-confidence violations, human-in-loop workflow, bulk approve/reject
- [ ] **Upload History (`/history`)** — list of all processed images with status, filter by date/camera/result
- [ ] **Camera Detail (`/cameras/[id]`)** — per-camera dashboard: preprocessing mode timeline, quality metrics graph, violation count, last processed frame
- [ ] **Settings (`/settings`)** — model profile selector, confidence thresholds, preprocessing budget, camera scene config editor
- [ ] **Batch Upload (`/batch`)** — multi-image upload with progress bar, parallel processing, results summary
- [ ] **Violation Detail (`/violations/[id]`)** — full violation record with evidence viewer, metadata, timeline, related violations from same plate
- [ ] **Dashboard (`/`)** — move KPIs + live feed + mini map from landing page to authenticated dashboard view
- [ ] **Error/Empty States** — proper empty states for all tables, loading skeletons, error boundaries
- [ ] **404 Page** — custom not-found page
- [ ] **Search** — global search across violations, plates, cameras (command palette / kbd shortcut)

## 5. Backend Gaps
- [ ] PostgreSQL schema + migrations (violations, cameras, evidence_packets, plates, processing_log)
- [ ] Persist violations to database after processing
- [ ] Serve violations from database in `/api/violations` (currently returns empty)
- [ ] Serve evidence from database in `/api/evidence/{id}` (currently returns mock)
- [ ] Serve analytics from database in `/api/analytics/*` (currently returns mock)
- [ ] Redis queue for async processing (batch uploads, video bursts)
- [ ] MinIO/S3 integration for evidence image storage
- [ ] User authentication (optional — hackathon may not need it)
- [ ] Rate limiting on `/api/process`
- [ ] Proper error handling + structured logging
- [ ] Health check includes model status, DB status, Redis status
- [ ] API pagination on all list endpoints

## 6. Model Improvements
- [ ] Train EfficientNetV2-S on helmet dataset (Open Images / custom Indian traffic)
- [ ] Train EfficientNetV2-S on seatbelt dataset
- [ ] Fine-tune YOLO11s on Indian plate dataset (IIIT-A, AOLP, custom)
- [ ] Add PARSeq as OCR fallback for low-confidence PaddleOCR results
- [ ] Add Real-ESRGAN plate crop super-resolution (Tier 3)
- [ ] Integrate Qwen-VL API for richer VLM descriptions
- [ ] Add emergency vehicle detection (siren/lights classifier)
- [ ] Add turban/pagdi detection (helmet exemption)
- [ ] Add signal state detection (red/yellow/green classifier)
- [x] D-FINE-L adapter implemented (falls back to YOLO11x when weights missing)
- [ ] Add model benchmarking script (latency, mAP on sample set)
- [ ] D-FINE-L weights download + integration test
- [ ] Qwen-VL external API integration (currently template fallback only)
- [ ] Plate detector fine-tune on Indian plates
- [ ] Helmet/seatbelt classifier training pipeline script

## 7. Testing
- [ ] Backend unit tests (pytest) for each pipeline module
- [ ] Backend integration tests for API endpoints
- [ ] Frontend component tests (Vitest + Testing Library)
- [ ] Frontend E2E tests (Vitest API tests — already have skeleton)
- [ ] Add Playwright browser E2E tests for critical flows
- [ ] Edge case test suite (turban, emergency vehicle, child-on-lap, dirty plate)
- [ ] Performance benchmarks (FPS, latency, memory)
- [ ] Load testing (concurrent camera streams)

## 8. Deployment & DevOps
- [ ] Docker Compose for full stack (backend + frontend + Redis + PostgreSQL + MinIO)
- [ ] Dockerfile for backend (Python + uv + model weights)
- [ ] Dockerfile for frontend (Next.js standalone build)
- [ ] Environment variable documentation
- [ ] CI/CD pipeline (GitHub Actions: lint, typecheck, test, build)
- [ ] Production deployment guide (GPU server setup, TensorRT conversion)
- [ ] Model weight download script (auto-fetch from HuggingFace/Ultralytics)
- [ ] Health check endpoint includes all model statuses
- [ ] Graceful shutdown handling (in-flight requests complete before exit)

## 9. Documentation
- [ ] README.md with project overview, setup instructions, demo screenshots
- [ ] API documentation (auto-generated from FastAPI OpenAPI)
- [ ] Model registry configuration guide
- [ ] Camera scene config guide (how to set stop-line, lane direction, etc.)
- [ ] Architecture diagram (system overview)
- [ ] Evidence packet format specification
- [ ] Violation detection logic documentation (each of 7 types)
- [ ] Deployment guide (local GPU, cloud, edge)
