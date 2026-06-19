import type { ProcessResult } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

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
