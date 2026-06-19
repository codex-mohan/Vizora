import type {
  AnalyticsSummary,
  CameraInfo,
  EvidencePacket,
  HeatmapCell,
  Hotspot,
  ProcessResult,
  RepeatOffender,
  ViolationListResponse,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function authHeaders(token?: string): HeadersInit {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
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
  return response.json() as Promise<T>;
}

export async function processMedia(file: File, cameraId: string, mode: "still_image" | "temporal_burst") {
  const form = new FormData();
  form.set("file", file);
  form.set("camera_id", cameraId);
  form.set("mode", mode);

  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Process request failed with ${response.status}`);
  }

  return (await response.json()) as ProcessResult;
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
  return apiFetch<EvidencePacket>(`/api/evidence/${packetId}`, { token });
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
  return apiFetch<HeatmapCell[]>("/api/analytics/heatmap", { token });
}

export async function fetchCameras(token?: string): Promise<CameraInfo[]> {
  return apiFetch<CameraInfo[]>("/api/cameras", { token });
}

export async function createCamera(data: {
  name: string;
  location_name?: string;
  latitude?: number;
  longitude?: number;
}, token?: string): Promise<CameraInfo> {
  return apiFetch<CameraInfo>("/api/cameras", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    token,
  });
}
