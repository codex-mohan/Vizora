"""Camera ingestion worker — grabs frames from RTSP/HTTP sources and runs inference."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from datetime import datetime, timezone
from io import BytesIO

import cv2
import httpx
import numpy as np
from PIL import Image

from core.realtime import realtime_bus
from pipeline.contracts import MediaInput, ProcessingMode

logger = logging.getLogger(__name__)


class CameraIngestionWorker:
    """Background worker that pulls frames from a camera source and runs inference.

    Tiered processing at ~25 FPS:
    - Every frame: detection + tracking (GPU, ~20ms)
    - Every Nth frame: pose + helmet/seatbelt classifiers (~25ms)
    - Reactive: ANPR only when violations are detected (~100ms but rare)
    """

    def __init__(
        self,
        camera_id: str,
        camera_name: str,
        source_type: str,
        source_url: str,
        pipeline,
        fps: float = 25.0,
        org_id: str | None = None,
    ) -> None:
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.source_type = source_type
        self.source_url = source_url
        self.pipeline = pipeline
        self.fps = fps
        self.org_id = org_id
        self._running = False
        self._task: asyncio.Task | None = None
        self._frame_count = 0
        self._classifier_interval = 3
        self._last_detections = []

    def _preview_data_url(self, image_bytes: bytes) -> tuple[str | None, int | None, int | None]:
        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            source_width, source_height = image.size
            image.thumbnail((960, 540))
            output = BytesIO()
            image.save(output, format="JPEG", quality=72, optimize=True)
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}", source_width, source_height
        except Exception:
            logger.warning("[ingest:%s] Could not encode live preview frame", self.camera_id)
            return None, None, None

    def _detection_payloads(self, result) -> list[dict]:
        return [
            {
                "id": detection.id,
                "label": detection.label.value,
                "confidence": detection.confidence,
                "bbox": detection.bbox.model_dump(),
                "metadata": detection.metadata,
            }
            for detection in result.detections
        ]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[ingest:%s] Started %s worker for %s at %.0f FPS",
                     self.camera_id, self.source_type, self.camera_name, self.fps)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[ingest:%s] Stopped", self.camera_id)

    async def _run_loop(self) -> None:
        if self.source_type == "rtsp":
            await self._loop_rtsp()
        elif self.source_type == "http_snapshot":
            await self._loop_http()
        elif self.source_type == "file_watcher":
            await self._loop_file_watcher()
        else:
            logger.error("[ingest:%s] Unknown source_type: %s", self.camera_id, self.source_type)

    async def _loop_rtsp(self) -> None:
        cap = cv2.VideoCapture(self.source_url)
        if not cap.isOpened():
            logger.error("[ingest:%s] Cannot open RTSP: %s", self.camera_id, self.source_url)
            return

        interval = 1.0 / self.fps
        logger.info("[ingest:%s] RTSP connected, running at %.0f FPS", self.camera_id, self.fps)

        while self._running:
            ret, frame = cap.read()
            if not ret:
                logger.warning("[ingest:%s] RTSP frame lost, reconnecting in 3s...", self.camera_id)
                cap.release()
                await asyncio.sleep(3)
                cap = cv2.VideoCapture(self.source_url)
                if not cap.isOpened():
                    await asyncio.sleep(5)
                continue

            success, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if success:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                await self._process_frame(buf.tobytes(), frame_rgb)

            await asyncio.sleep(interval)

        cap.release()

    async def _loop_http(self) -> None:
        interval = 1.0 / self.fps
        async with httpx.AsyncClient(timeout=10.0) as client:
            while self._running:
                try:
                    resp = await client.get(self.source_url)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        img = Image.open(BytesIO(resp.content)).convert("RGB")
                        await self._process_frame(resp.content, np.asarray(img))
                except Exception as e:
                    logger.warning("[ingest:%s] HTTP error: %s", self.camera_id, e)
                await asyncio.sleep(interval)

    async def _loop_file_watcher(self) -> None:
        import os
        seen: set[str] = set()
        watch_dir = self.source_url
        if not os.path.isdir(watch_dir):
            logger.error("[ingest:%s] Directory not found: %s", self.camera_id, watch_dir)
            return

        interval = 1.0 / self.fps
        while self._running:
            try:
                for fname in os.listdir(watch_dir):
                    if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                        continue
                    fpath = os.path.join(watch_dir, fname)
                    if fpath in seen:
                        continue
                    seen.add(fpath)
                    with open(fpath, "rb") as f:
                        data = f.read()
                    img = Image.open(BytesIO(data)).convert("RGB")
                    await self._process_frame(data, np.asarray(img))
                    if len(seen) > 10000:
                        seen.clear()
            except Exception as e:
                logger.warning("[ingest:%s] File watcher error: %s", self.camera_id, e)
            await asyncio.sleep(interval)

    async def _process_frame(self, image_bytes: bytes, img_array: np.ndarray) -> None:
        self._frame_count += 1
        t0 = time.perf_counter()
        try:
            media = MediaInput(
                filename=f"frame-{self.camera_id}.jpg",
                data=image_bytes,
                camera_id=self.camera_id,
                timestamp=datetime.now(timezone.utc),
                mode=ProcessingMode.STILL_IMAGE,
                content_type="image/jpeg",
                realtime_preview=True,
                generate_artifacts=False,
            )

            result = await asyncio.get_event_loop().run_in_executor(
                None, self.pipeline.process, media
            )

            latency_ms = (time.perf_counter() - t0) * 1000
            frame_preview, frame_width, frame_height = self._preview_data_url(image_bytes)

            event = {
                "type": "frame_processed",
                "camera_id": self.camera_id,
                "camera_name": self.camera_name,
                "frame_index": self._frame_count,
                "frame_width": frame_width,
                "frame_height": frame_height,
                "timestamp": result.timestamp.isoformat(),
                "detections": len(result.detections),
                "live_detections": self._detection_payloads(result),
                "violations": len(result.violations),
                "plates": len(result.plates),
                "latency_ms": round(latency_ms, 1),
                "model_profile": result.model_profile,
                "violation_types": [v.violation_type.value for v in result.violations],
                "frame_preview": frame_preview,
                "annotated_preview": False,
            }
            realtime_bus.publish(event)

            if result.violations:
                logger.info(
                    "[ingest:%s] frame #%d | %dms | dets=%d violations=%d plates=%d | %s",
                    self.camera_id, self._frame_count, latency_ms,
                    len(result.detections), len(result.violations), len(result.plates),
                    ", ".join(v.violation_type.value for v in result.violations),
                )

        except Exception as e:
            logger.error("[ingest:%s] Frame error: %s", self.camera_id, e)


class IngestionManager:
    def __init__(self) -> None:
        self._workers: dict[str, CameraIngestionWorker] = {}

    async def start_camera(
        self, camera_id: str, camera_name: str, source_type: str,
        source_url: str, pipeline, org_id: str | None = None, fps: float = 8.0,
    ) -> None:
        if camera_id in self._workers:
            await self.stop_camera(camera_id)
        worker = CameraIngestionWorker(
            camera_id=camera_id, camera_name=camera_name,
            source_type=source_type, source_url=source_url,
            pipeline=pipeline, fps=fps, org_id=org_id,
        )
        self._workers[camera_id] = worker
        await worker.start()

    async def stop_camera(self, camera_id: str) -> None:
        worker = self._workers.pop(camera_id, None)
        if worker:
            await worker.stop()

    async def stop_all(self) -> None:
        for camera_id in list(self._workers.keys()):
            await self.stop_camera(camera_id)

    def active_cameras(self) -> list[str]:
        return list(self._workers.keys())


ingestion_manager = IngestionManager()
