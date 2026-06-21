import type {
  AnalyticsSummary,
  CameraInfo,
  EvidencePacket,
  HeatmapCell,
  Hotspot,
  HotspotMapResponse,
  ProcessResult,
  RepeatOffender,
  ViolationListResponse,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function resolveUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_BASE_URL}${url}`;
}

function resolveUrls(urls: string[]): string[] {
  return urls.map((u) => resolveUrl(u) ?? u);
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("vizora_token");
}

function authHeaders(token?: string): HeadersInit {
  const t = token ?? getStoredToken();
  if (!t) return {};
  return { Authorization: `Bearer ${t}` };
}

async function apiFetch<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const { token, ...fetchInit } = init ?? {};
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchInit,
    headers: {
      ...authHeaders(token),
      ...fetchInit.headers,
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  const text = await response.text();
  if (!text.trim()) return undefined as T;
  return JSON.parse(text) as T;
}

export async function processMedia(file: File, cameraId: string, mode: "still_image" | "temporal_burst") {
  const form = new FormData();
  form.set("file", file);
  form.set("camera_id", cameraId);
  form.set("mode", mode);
  return apiFetch<ProcessResult>("/api/process", { method: "POST", body: form });
}

export function realtimeEventsUrl() {
  return `${API_BASE_URL}/api/process/events`;
}

export async function fetchViolations(params: {
  page?: number;
  size?: number;
  violation_type?: string;
  camera_id?: string;
  min_confidence?: number;
  date_from?: string;
  date_to?: string;
  plate_search?: string;
  review_required?: boolean;
  status?: string;
  token?: string;
}): Promise<ViolationListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page !== undefined) searchParams.set("page", String(params.page));
  if (params.size !== undefined) searchParams.set("size", String(params.size));
  if (params.violation_type) searchParams.set("violation_type", params.violation_type);
  if (params.camera_id) searchParams.set("camera_id", params.camera_id);
  if (params.min_confidence !== undefined) searchParams.set("min_confidence", String(params.min_confidence));
  if (params.date_from) searchParams.set("date_from", params.date_from);
  if (params.date_to) searchParams.set("date_to", params.date_to);
  if (params.plate_search) searchParams.set("plate_search", params.plate_search);
  if (params.review_required !== undefined) searchParams.set("review_required", String(params.review_required));
  if (params.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return apiFetch<ViolationListResponse>(`/api/violations${qs ? `?${qs}` : ""}`, { token: params.token });
}

export async function fetchEvidence(packetId: string, token?: string): Promise<EvidencePacket> {
  const data = await apiFetch<EvidencePacket>(`/api/evidence/${packetId}`, { token });
  return {
    ...data,
    frame_urls: resolveUrls(data.frame_urls),
    plate_crop_url: resolveUrl(data.plate_crop_url),
    annotated_frame_url: resolveUrl(data.annotated_frame_url),
  };
}

export async function updateViolationStatus(
  violationId: string,
  status: "approved" | "rejected" | "escalated",
  token?: string,
): Promise<void> {
  await apiFetch(`/api/violations/${violationId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
    token,
  });
}

export async function fetchAnalyticsSummary(params?: {
  date_from?: string;
  date_to?: string;
  token?: string;
}): Promise<AnalyticsSummary> {
  const searchParams = new URLSearchParams();
  if (params?.date_from) searchParams.set("date_from", params.date_from);
  if (params?.date_to) searchParams.set("date_to", params.date_to);
  const qs = searchParams.toString();
  return apiFetch<AnalyticsSummary>(`/api/analytics/summary${qs ? `?${qs}` : ""}`, { token: params?.token });
}

export async function fetchHotspots(limit?: number, token?: string): Promise<Hotspot[]> {
  const qs = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch<Hotspot[]>(`/api/analytics/hotspots${qs}`, { token });
}

export async function fetchRepeatOffenders(limit?: number, token?: string): Promise<RepeatOffender[]> {
  const qs = limit !== undefined ? `?limit=${limit}` : "";
  return apiFetch<RepeatOffender[]>(`/api/analytics/repeat-offenders${qs}`, { token });
}

export async function fetchDayHourHeatmap(token?: string): Promise<HeatmapCell[]> {
  return apiFetch<HeatmapCell[]>("/api/analytics/day-hour-heatmap", { token });
}

export async function fetchHotspotMap(params?: {
  limit?: number;
  date_from?: string;
  date_to?: string;
  camera_id?: string;
  violation_type?: string;
  token?: string;
}): Promise<HotspotMapResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params?.date_from) searchParams.set("date_from", params.date_from);
  if (params?.date_to) searchParams.set("date_to", params.date_to);
  if (params?.camera_id) searchParams.set("camera_id", params.camera_id);
  if (params?.violation_type) searchParams.set("violation_type", params.violation_type);
  const qs = searchParams.toString();
  return apiFetch<HotspotMapResponse>(`/api/analytics/hotspot-map${qs ? `?${qs}` : ""}`, {
    token: params?.token,
  });
}

export async function fetchCameras(token?: string): Promise<CameraInfo[]> {
  return apiFetch<CameraInfo[]>("/api/cameras", { token });
}

export async function createCamera(data: {
  name: string;
  location_name?: string;
  latitude?: number;
  longitude?: number;
  source_type?: string;
  source_url?: string;
  model_profile?: string;
  enabled?: boolean;
}, token?: string): Promise<CameraInfo> {
  return apiFetch<CameraInfo>("/api/cameras", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    token,
  });
}

export async function updateCamera(
  cameraId: string,
  data: {
    name?: string;
    location_name?: string;
    latitude?: number;
    longitude?: number;
    source_type?: string;
    source_url?: string;
    model_profile?: string;
    enabled?: boolean;
    status?: string;
  },
  token?: string,
): Promise<CameraInfo> {
  return apiFetch<CameraInfo>(`/api/cameras/${cameraId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    token,
  });
}

export async function deleteCamera(cameraId: string, token?: string): Promise<void> {
  await apiFetch(`/api/cameras/${cameraId}`, { method: "DELETE", token });
}
