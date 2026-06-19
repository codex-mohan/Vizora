import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const currentDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(currentDir, "..", "..", "..");
const backendDir = resolve(repoRoot, "backend");
const baseUrl = process.env.E2E_BACKEND_URL ?? "http://127.0.0.1:8012";

let backend: ChildProcessWithoutNullStreams | undefined;
let ownsBackend = false;

async function isHealthy(): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForBackend(): Promise<void> {
  for (let attempt = 0; attempt < 90; attempt += 1) {
    if (await isHealthy()) {
      return;
    }
    await delay(1_000);
  }
  throw new Error("Backend did not become healthy in time");
}

function startBackend(): void {
  backend = spawn(
    "uv",
    ["run", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", new URL(baseUrl).port],
    {
      cwd: backendDir,
      env: { ...process.env, TVD_DEBUG: "false" },
      shell: process.platform === "win32",
    },
  );
  ownsBackend = true;
}

function demoPng(): Blob {
  const base64 =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=";
  const bytes = Uint8Array.from(Buffer.from(base64, "base64"));
  return new Blob([bytes], { type: "image/png" });
}

beforeAll(async () => {
  if (!process.env.E2E_BACKEND_URL) {
    startBackend();
  } else if (!(await isHealthy())) {
    throw new Error(`Backend is not healthy at ${baseUrl}`);
  }
  await waitForBackend();
});

afterAll(() => {
  if (ownsBackend && backend) {
    backend.kill();
  }
});

describe("process API", () => {
  it("accepts an uploaded image and returns the inference contract", async () => {
    const form = new FormData();
    form.set("file", demoPng(), "demo.png");
    form.set("camera_id", "demo-camera");
    form.set("mode", "still_image");

    const response = await fetch(`${baseUrl}/api/process`, {
      method: "POST",
      body: form,
    });

    expect(response.status).toBe(200);
    const payload = await response.json();

    expect(payload.request_id).toMatch(/^req-/);
    expect(payload.camera_id).toBe("demo-camera");
    expect(payload.mode).toBe("still_image");
    expect(payload.evidence_packet_id).toMatch(/^ev-/);
    expect(payload.model_profile).toBe("mvp");
    expect(Array.isArray(payload.detections)).toBe(true);
    expect(Array.isArray(payload.plates)).toBe(true);
    expect(Array.isArray(payload.violations)).toBe(true);
    expect(payload.quality.score).toBeGreaterThanOrEqual(0);
    expect(payload.quality.score).toBeLessThanOrEqual(1);
  });
});
