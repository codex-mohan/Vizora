"use client";

import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Camera,
  Globe,
  Loader2,
  Play,
  Radio,
  RefreshCw,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchCameras, processMedia, realtimeEventsUrl, updateCamera } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { CameraInfo, DetectedObject, ProcessResult } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ImageSize = {
  width: number;
  height: number;
};

type SourceMode = "upload" | "url" | "camera";

type LiveEvent = {
  type?: string;
  camera_id?: string;
  camera_name?: string;
  timestamp?: string;
  frame_index?: number;
  frame_width?: number | null;
  frame_height?: number | null;
  detections?: number;
  live_detections?: DetectedObject[];
  violations?: number;
  plates?: number;
  latency_ms?: number;
  violation_count?: number;
  evidence_packet_id?: string;
  frame_preview?: string | null;
  annotated_preview?: boolean;
};

function confidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function sourceLabel(camera: CameraInfo) {
  if (camera.source_type === "rtsp") return "RTSP";
  if (camera.source_type === "http_snapshot") return "HTTP";
  if (camera.source_type === "file_watcher") return "Folder";
  return camera.source_type ?? "Upload";
}

function detectionStyle(label: string) {
  const normalized = label.toLowerCase();
  if (normalized === "motorcycle" || normalized === "car" || normalized === "bus" || normalized === "truck" || normalized === "auto" || normalized === "bicycle") {
    return {
      name: "Vehicle",
      swatch: "bg-sky-300",
      border: "border-sky-300/90",
      fill: "bg-sky-300/10",
      label: "border-sky-300/40 text-sky-100",
      text: "text-sky-300",
      shadow: "shadow-[0_0_28px_rgba(125,211,252,0.26)]",
    };
  }
  if (normalized === "rider" || normalized === "driver") {
    return {
      name: "Rider",
      swatch: "bg-violet-300",
      border: "border-violet-300/90",
      fill: "bg-violet-300/10",
      label: "border-violet-300/40 text-violet-100",
      text: "text-violet-300",
      shadow: "shadow-[0_0_28px_rgba(167,139,250,0.28)]",
    };
  }
  if (normalized === "pedestrian") {
    return {
      name: "Pedestrian",
      swatch: "bg-lime-300",
      border: "border-lime-300/90",
      fill: "bg-lime-300/10",
      label: "border-lime-300/40 text-lime-100",
      text: "text-lime-300",
      shadow: "shadow-[0_0_28px_rgba(190,242,100,0.2)]",
    };
  }
  if (normalized === "plate") {
    return {
      name: "Plate",
      swatch: "bg-amber-300",
      border: "border-amber-300/90",
      fill: "bg-amber-300/10",
      label: "border-amber-300/40 text-amber-100",
      text: "text-amber-300",
      shadow: "shadow-[0_0_28px_rgba(252,211,77,0.22)]",
    };
  }
  return {
    name: "Other",
    swatch: "bg-slate-300",
    border: "border-slate-300/80",
    fill: "bg-slate-300/10",
    label: "border-slate-300/30 text-slate-100",
    text: "text-slate-300",
    shadow: "shadow-[0_0_24px_rgba(203,213,225,0.16)]",
  };
}

const DETECTION_LEGEND = [
  detectionStyle("motorcycle"),
  detectionStyle("rider"),
  detectionStyle("pedestrian"),
  detectionStyle("plate"),
];

function BoxOverlay({ detection, imageSize }: { detection: DetectedObject; imageSize: ImageSize | null }) {
  if (!imageSize || !detection.bbox) return null;

  const style = detectionStyle(detection.label);
  const left = (detection.bbox.x1 / imageSize.width) * 100;
  const top = (detection.bbox.y1 / imageSize.height) * 100;
  const width = ((detection.bbox.x2 - detection.bbox.x1) / imageSize.width) * 100;
  const height = ((detection.bbox.y2 - detection.bbox.y1) / imageSize.height) * 100;

  return (
    <div
      className={`absolute rounded-lg border ${style.border} ${style.fill} ${style.shadow}`}
      style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
    >
      <span className={`absolute -top-7 left-0 rounded-md border bg-slate-950/90 px-2 py-1 font-metadata text-[10px] uppercase tracking-[0.18em] backdrop-blur ${style.label}`}>
        {detection.label} {confidence(detection.confidence)}
      </span>
    </div>
  );
}

function SourceModeTab({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Upload;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 rounded-xl px-4 py-2.5 font-metadata text-xs uppercase tracking-[0.18em] transition-colors ${
        active
          ? "border border-violet-300/30 bg-violet-300/15 text-violet-200"
          : "border border-transparent text-slate-500 hover:border-white/[0.06] hover:text-slate-300"
      }`}
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  );
}

export default function ProcessPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [sourceMode, setSourceMode] = useState<SourceMode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [cameraId, setCameraId] = useState("demo-camera");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<ImageSize | null>(null);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [camerasLoading, setCamerasLoading] = useState(false);
  const [cameraActionLoading, setCameraActionLoading] = useState<string | null>(null);
  const [liveEvents, setLiveEvents] = useState<LiveEvent[]>([]);
  const [latestLiveFrame, setLatestLiveFrame] = useState<LiveEvent | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const liveLastSeenRef = useRef(0);
  const objectUrlRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    async function loadCameras() {
      setCamerasLoading(true);
      try {
        const data = await fetchCameras();
        if (cancelled) return;
        setCameras(data);
        if (data.length > 0) {
          setCameraId((current) => (current === "demo-camera" ? data[0].id : current));
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load cameras");
      } finally {
        if (!cancelled) setCamerasLoading(false);
      }
    }

    loadCameras();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (sourceMode !== "camera" || !cameraId) return;

    const events = new EventSource(realtimeEventsUrl());
    events.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as LiveEvent;
        if (payload.camera_id && payload.camera_id !== cameraId) return;
        liveLastSeenRef.current = Date.now();
        setLiveError(null);
        setLiveEvents((prev) => [payload, ...prev].slice(0, 8));
        if (payload.frame_preview) setLatestLiveFrame(payload);
      } catch {
        // Ignore malformed keepalive/event payloads.
      }
    };
    events.onerror = () => {
      if (!liveLastSeenRef.current || Date.now() - liveLastSeenRef.current > 5000) {
        setLiveError("Live event stream is disconnected. Make sure the backend is running.");
      }
    };

    return () => events.close();
  }, [sourceMode, cameraId]);

  const selectedCamera = useMemo(
    () => cameras.find((camera) => camera.id === cameraId) ?? null,
    [cameras, cameraId],
  );
  const topDetections = useMemo(() => result?.detections ?? [], [result]);

  function handleFileChange(nextFile: File | null) {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    setFile(nextFile);
    setResult(null);
    setImageSize(null);
    if (!nextFile) {
      objectUrlRef.current = null;
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(nextFile);
    objectUrlRef.current = url;
    setPreviewUrl(url);
  }

  async function fetchUrlAsFile(url: string, nameHint: string): Promise<File> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to fetch: ${response.status} ${response.statusText}`);
    const blob = await response.blob();
    const ext = blob.type.includes("video") ? ".mp4" : ".jpg";
    return new File([blob], `${nameHint}${ext}`, { type: blob.type || "image/jpeg" });
  }

  async function handleUrlSubmit() {
    if (!urlInput.trim()) return;
    setUrlLoading(true);
    setError(null);
    try {
      const fetchedFile = await fetchUrlAsFile(urlInput.trim(), "cctv-frame");
      handleFileChange(fetchedFile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch URL");
    } finally {
      setUrlLoading(false);
    }
  }

  async function refreshCameras() {
    setCamerasLoading(true);
    setError(null);
    try {
      const data = await fetchCameras();
      setCameras(data);
      if (!data.some((camera) => camera.id === cameraId) && data.length > 0) {
        setCameraId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh cameras");
    } finally {
      setCamerasLoading(false);
    }
  }

  async function restartCamera(camera: CameraInfo) {
    setCameraActionLoading(camera.id);
    setLiveEvents([]);
    setLatestLiveFrame(null);
    liveLastSeenRef.current = 0;
    setLiveError(null);
    try {
      const updated = await updateCamera(camera.id, {
        name: camera.name,
        source_type: camera.source_type ?? undefined,
        source_url: camera.source_url ?? undefined,
        enabled: true,
      });
      setCameras((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setCameraId(updated.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start camera ingestion");
    } finally {
      setCameraActionLoading(null);
    }
  }

  const liveFrameSize = latestLiveFrame?.frame_width && latestLiveFrame.frame_height
    ? { width: latestLiveFrame.frame_width, height: latestLiveFrame.frame_height }
    : null;

  async function submit() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await processMedia(file, cameraId, "still_image"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Processing failed");
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const droppedFile = event.dataTransfer.files?.[0] ?? null;
    if (droppedFile && droppedFile.type.startsWith("image/")) {
      handleFileChange(droppedFile);
    }
  }

  return (
    <main className="px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="space-y-2">
          <h1 className="font-heading text-3xl font-semibold tracking-[-0.03em] text-white">
            Process Evidence
          </h1>
          <p className="text-base leading-7 text-slate-400">
            Upload a frame, fetch a snapshot URL, or use a registered live camera from Settings.
          </p>
        </header>

        <section className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <SourceModeTab active={sourceMode === "upload"} onClick={() => setSourceMode("upload")} icon={Upload} label="Upload Evidence" />
            <SourceModeTab active={sourceMode === "url"} onClick={() => setSourceMode("url")} icon={Globe} label="Snapshot URL" />
            <SourceModeTab active={sourceMode === "camera"} onClick={() => setSourceMode("camera")} icon={Radio} label="Live Camera" />
          </div>

          {sourceMode === "upload" && (
            <div
              className="flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-white/[0.08] bg-white/[0.02] p-12 transition-colors hover:border-violet-300/30 hover:bg-violet-300/[0.03]"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-5">
                <Upload className="size-8 text-slate-500" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-slate-300">
                  Drop an image here or click to browse
                </p>
                <p className="mt-1 text-xs text-slate-600">PNG, JPG, or WEBP</p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
              />
            </div>
          )}

          {sourceMode === "url" && (
            <div className="space-y-4 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6">
              <div className="flex items-center gap-3">
                <div className="grid size-10 place-items-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
                  <Camera className="size-5 text-slate-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">HTTP Snapshot URL</p>
                  <p className="text-xs text-slate-500">
                    Fetch one image/video snapshot and run still-image inference against the selected camera.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://cctv-server/snapshot.jpg"
                  className="h-11 flex-1 border-white/[0.06] bg-white/[0.03]"
                  onKeyDown={(e) => e.key === "Enter" && handleUrlSubmit()}
                />
                <Button
                  onClick={handleUrlSubmit}
                  disabled={!urlInput.trim() || urlLoading}
                  className="h-11 cursor-pointer bg-violet-400 text-[#100f18] hover:bg-violet-300"
                >
                  {urlLoading ? <Loader2 className="size-4 animate-spin" /> : <Globe className="size-4" />}
                </Button>
              </div>
            </div>
          )}

          {sourceMode === "camera" && (
            <div className="space-y-4 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-xl border border-lime-300/20 bg-lime-300/10">
                    <Radio className="size-5 text-lime-300" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">Registered Camera Sources</p>
                    <p className="text-xs text-slate-500">
                      Cameras added in Settings appear here. RTSP ingestion runs in the backend.
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={refreshCameras}
                  disabled={camerasLoading}
                  className="h-9 cursor-pointer text-xs"
                >
                  {camerasLoading ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : <RefreshCw className="mr-1.5 size-3.5" />}
                  Refresh
                </Button>
              </div>

              {!cameras.length && !camerasLoading ? (
                <div className="rounded-xl border border-dashed border-white/[0.08] bg-white/[0.02] p-6 text-sm text-slate-400">
                  No cameras found. Add your RTSP source in Settings first, save it, then return here.
                </div>
              ) : (
                <div className="grid gap-3">
                  {cameras.map((camera) => {
                    const selected = camera.id === cameraId;
                    const canIngest = Boolean(camera.source_url && camera.enabled);
                    return (
                      <button
                        key={camera.id}
                        type="button"
                        onClick={() => setCameraId(camera.id)}
                        className={`rounded-2xl border p-4 text-left transition-colors ${
                          selected
                            ? "border-violet-300/35 bg-violet-300/10"
                            : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]"
                        }`}
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div className="min-w-0 space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="font-medium text-white">{camera.name}</p>
                              <Badge className={camera.enabled ? "bg-lime-300/15 text-lime-300" : "bg-slate-300/10 text-slate-500"}>
                                {camera.enabled ? "Enabled" : "Disabled"}
                              </Badge>
                              <Badge variant="outline" className="border-white/[0.08] text-slate-400">
                                {sourceLabel(camera)}
                              </Badge>
                              {selected && <Badge className="bg-violet-300 text-slate-950">Selected</Badge>}
                            </div>
                            <p className="truncate font-mono text-xs text-slate-500">{camera.source_url || "No source URL configured"}</p>
                            <p className="text-xs text-slate-600">{camera.location_name || camera.id}</p>
                          </div>
                          <div
                            className="flex shrink-0 gap-2"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <Button
                              size="sm"
                              onClick={() => restartCamera(camera)}
                              disabled={!canIngest || cameraActionLoading === camera.id}
                              className="cursor-pointer bg-lime-300 text-slate-950 hover:bg-lime-200"
                            >
                              {cameraActionLoading === camera.id ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : <Play className="mr-1.5 size-3.5" />}
                              Start
                            </Button>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {selectedCamera && (
                <div className="rounded-2xl border border-white/[0.06] bg-slate-950/60 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Active source</p>
                      <p className="mt-1 text-sm text-slate-200">{selectedCamera.name}</p>
                    </div>
                    <Badge className="bg-sky-300/15 text-sky-300">
                      {selectedCamera.current_mode || "CLEAN"} mode
                    </Badge>
                  </div>
                  <div className="mt-4 space-y-2">
                    <div className="overflow-hidden rounded-2xl border border-white/[0.06] bg-black">
                      {latestLiveFrame?.frame_preview ? (
                        <div className="relative">
                          <img
                            src={latestLiveFrame.frame_preview}
                            alt="Live processed traffic frame"
                            className="block w-full bg-black object-contain"
                          />
                          {(latestLiveFrame.live_detections ?? []).map((detection) => (
                            <BoxOverlay
                              key={detection.id}
                              detection={detection}
                              imageSize={liveFrameSize}
                            />
                          ))}
                          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
                            <Badge className="bg-lime-300 text-slate-950">
                              Live frame #{latestLiveFrame.frame_index ?? "-"}
                            </Badge>
                            <Badge className="bg-slate-950/80 text-slate-200">
                              {latestLiveFrame.annotated_preview ? "Annotated" : "Raw preview"}
                            </Badge>
                          </div>
                          <div className="absolute bottom-3 left-3 right-3 flex flex-wrap gap-2 rounded-xl border border-white/10 bg-slate-950/75 p-2 text-xs text-slate-200 backdrop-blur">
                            <span>{latestLiveFrame.detections ?? 0} detections</span>
                            <span>{latestLiveFrame.plates ?? 0} plates</span>
                            <span>{latestLiveFrame.violations ?? latestLiveFrame.violation_count ?? 0} violations</span>
                            {latestLiveFrame.latency_ms != null && <span>{latestLiveFrame.latency_ms} ms</span>}
                          </div>
                        </div>
                      ) : (
                        <div className="flex aspect-video flex-col items-center justify-center gap-3 bg-slate-950 text-center">
                          <Radio className="size-8 animate-pulse text-slate-600" />
                          <div>
                            <p className="text-sm font-medium text-slate-300">Waiting for live processed frames</p>
                            <p className="mt-1 text-xs text-slate-600">
                              Press Start after your RTSP/file source is reachable. Frames will appear here as SSE previews.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    <p className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Live events</p>
                    {liveError && <p className="text-sm text-amber-200">{liveError}</p>}
                    {!liveEvents.length && !liveError ? (
                      <p className="text-sm text-slate-500">
                        Waiting for frames. Start the RTSP loop and press Start on this camera.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {liveEvents.map((event, index) => (
                          <div
                            key={`${event.timestamp ?? index}-${index}`}
                            className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-xs text-slate-300"
                          >
                            <span className="font-mono text-slate-500">{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "event"}</span>
                            <span>{event.type ?? "frame"}</span>
                            <span>{event.detections ?? 0} detections</span>
                            <span>{event.violations ?? event.violation_count ?? 0} violations</span>
                            {event.latency_ms != null && <span>{event.latency_ms} ms</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {sourceMode !== "camera" && cameras.length > 0 && (
            <div className="space-y-2">
              <label className="font-metadata text-xs uppercase tracking-widest text-slate-500">
                Camera context
              </label>
              <div className="grid gap-2 sm:grid-cols-2">
                {cameras.map((camera) => (
                  <button
                    key={camera.id}
                    type="button"
                    onClick={() => setCameraId(camera.id)}
                    className={`rounded-xl border p-3 text-left transition-colors ${
                      camera.id === cameraId
                        ? "border-violet-300/35 bg-violet-300/10"
                        : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]"
                    }`}
                  >
                    <p className="text-sm font-medium text-slate-200">{camera.name}</p>
                    <p className="mt-1 truncate font-mono text-[10px] text-slate-600">{camera.id}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {sourceMode !== "camera" && cameras.length === 0 && (
            <div className="space-y-2">
              <label className="font-metadata text-xs uppercase tracking-widest text-slate-500">
                Camera ID
              </label>
              <Input
                value={cameraId}
                onChange={(event) => setCameraId(event.target.value)}
                className="h-11 border-white/[0.06] bg-white/[0.03]"
              />
            </div>
          )}

          {previewUrl && (
            <div className="relative w-full rounded-xl border border-white/[0.06]">
              <img
                ref={imageRef}
                src={previewUrl}
                alt="Traffic evidence"
                className="block max-h-[520px] w-full rounded-xl object-contain"
                onLoad={() => {
                  const image = imageRef.current;
                  if (image) setImageSize({ width: image.naturalWidth, height: image.naturalHeight });
                }}
              />
              {topDetections.map((detection) => (
                <BoxOverlay key={detection.id} detection={detection} imageSize={imageSize} />
              ))}
            </div>
          )}

          {file && (
            <p className="text-center font-metadata text-xs uppercase tracking-widest text-slate-500">
              {file.name}
            </p>
          )}

          {result && (
            <div className="flex flex-wrap justify-center gap-2">
              {DETECTION_LEGEND.map((item) => (
                <span
                  key={item.name}
                  className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1 font-metadata text-[10px] uppercase tracking-[0.18em] text-slate-400"
                >
                  <span className={`size-2 rounded-full ${item.swatch}`} />
                  {item.name}
                </span>
              ))}
            </div>
          )}

          {sourceMode !== "camera" && (
            <Button
              disabled={!file || loading}
              onClick={submit}
              className="h-12 w-full cursor-pointer bg-violet-400 text-[#100f18] hover:bg-violet-300"
            >
              {loading ? (
                <Loader2 className="mr-2 size-4 animate-spin" />
              ) : (
                <Activity className="mr-2 size-4" />
              )}
              Run Inference
            </Button>
          )}

          {error && (
            <div className="rounded-2xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-100">
              {error}
            </div>
          )}
        </section>

        {result && (
          <section className="space-y-6">
            <div className="border-t border-white/[0.06]" />

            <div className="flex items-center justify-between">
              <h2 className="font-heading text-xl font-semibold text-white">Results</h2>
              <Badge
                className={
                  result.review_required
                    ? "bg-amber-300 text-[#100f18]"
                    : "bg-lime-300 text-[#100f18]"
                }
              >
                {result.review_required ? "Review required" : "Auto clear"}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                <p className="font-metadata text-xs uppercase tracking-widest text-slate-500">Objects</p>
                <p className="mt-2 font-heading text-3xl text-white">{result.detections.length}</p>
              </div>
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                <p className="font-metadata text-xs uppercase tracking-widest text-slate-500">OCR Plates</p>
                <p className="mt-2 font-heading text-3xl text-white">{result.plates.length}</p>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="font-metadata text-xs uppercase tracking-widest text-slate-500">Detections</h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {topDetections.map((detection) => (
                  <div
                    key={detection.id}
                    className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2 font-medium capitalize text-slate-100">
                        <span className={`size-2 rounded-full ${detectionStyle(detection.label).swatch}`} />
                        {detection.label}
                      </span>
                      <span className={`font-metadata text-xs ${detectionStyle(detection.label).text}`}>
                        {confidence(detection.confidence)}
                      </span>
                    </div>
                    {detection.bbox && (
                      <p className="mt-2 font-metadata text-xs text-slate-600">
                        {Math.round(detection.bbox.x1)}, {Math.round(detection.bbox.y1)} -{" "}
                        {Math.round(detection.bbox.x2)}, {Math.round(detection.bbox.y2)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="flex items-center gap-2 font-metadata text-xs uppercase tracking-widest text-slate-500">
                <ShieldCheck className="size-3.5 text-amber-300" /> OCR Candidates
              </h3>
              {result.plates.length ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {result.plates.map((plate, index) => (
                    <div
                      key={`${plate.plate_text}-${index}`}
                      className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-3"
                    >
                      <p className="font-metadata text-sm text-amber-100">{plate.plate_text}</p>
                      <p className="mt-1 text-xs text-slate-600">
                        confidence {confidence(plate.confidence)}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-600">No OCR candidates found.</p>
              )}
            </div>

            {result.review_required && (
              <div className="flex items-start gap-3 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-amber-100">
                <AlertTriangle className="mt-0.5 size-5 shrink-0" />
                <div>
                  <p className="font-medium">Human review recommended</p>
                  <p className="mt-1 text-sm text-amber-100/75">
                    {result.review_reasons.join(", ") || "Low-confidence evidence requires reviewer confirmation."}
                  </p>
                </div>
              </div>
            )}

            {result.description && (
              <div className="space-y-3">
                <h3 className="flex items-center gap-2 font-metadata text-xs uppercase tracking-widest text-slate-500">
                  <BrainCircuit className="size-3.5 text-violet-300" /> Evidence Summary
                </h3>
                <div className="rounded-2xl border border-violet-300/15 bg-violet-300/[0.04] p-4">
                  <p className="text-sm leading-6 text-slate-200">{result.description}</p>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <p className="font-metadata text-xs uppercase tracking-widest text-slate-500">
                Evidence Packet ID
              </p>
              <p className="break-all font-mono text-xs text-violet-200/80">
                {result.evidence_packet_id}
              </p>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
