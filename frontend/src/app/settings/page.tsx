"use client";

import {
  Camera,
  Cpu,
  Globe,
  KeyRound,
  Loader2,
  Mail,
  Monitor,
  Plus,
  Save,
  Settings2,
  Shield,
  ShieldCheck,
  Signal,
  Trash2,
  User,
  Video,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";

import { useAuth } from "@/lib/auth-context";
import { fetchCameras, createCamera, deleteCamera, updateCamera } from "@/lib/api";
import { ORG_SETTINGS_KEY } from "@/lib/org-settings";
import type { CameraInfo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type SourceType = "http_snapshot" | "rtsp" | "file_watcher";

interface CameraSource {
  id: string;
  name: string;
  url: string;
  source_type: SourceType;
  location_name: string;
  latitude: string;
  longitude: string;
  model_profile: string;
  enabled: boolean;
}

interface OrgSettings {
  default_model_profile: string;
  confidence_threshold: string;
  review_threshold: string;
  preprocessing_mode: string;
  enable_plate_recognition: boolean;
  enable_helmet_detection: boolean;
  enable_seatbelt_detection: boolean;
  evidence_retention_days: string;
  default_location_name: string;
  default_location_latitude: string;
  default_location_longitude: string;
}

const SOURCE_TYPE_LABELS: Record<SourceType, { label: string; icon: typeof Camera; description: string }> = {
  http_snapshot: { label: "HTTP Snapshot", icon: Globe, description: "Periodic HTTP image fetch from CCTV endpoint" },
  rtsp: { label: "RTSP Stream", icon: Video, description: "RTSP video stream (requires backend ingestion)" },
  file_watcher: { label: "File Watcher", icon: Monitor, description: "Watch a directory for new image files" },
};

const MODEL_PROFILES = [
  { value: "fast", label: "Fast (YOLO)", description: "YOLO11-S \u2014 speed optimized, real-time" },
  { value: "accuracy", label: "Accuracy (RT-DETRv2)", description: "RT-DETRv2 \u2014 higher accuracy, slower" },
  { value: "review", label: "Review (D-FINE)", description: "D-FINE \u2014 best accuracy for human review queue" },
];

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  admin: { label: "Administrator", color: "bg-violet-300/15 text-violet-300" },
  reviewer: { label: "Reviewer", color: "bg-sky-300/15 text-sky-300" },
  analyst: { label: "Analyst", color: "bg-amber-300/15 text-amber-300" },
  operator: { label: "Operator", color: "bg-lime-300/15 text-lime-300" },
  viewer: { label: "Viewer", color: "bg-slate-300/15 text-slate-400" },
};

const CAMERA_DRAFT_KEY = "vizora_camera_sources_draft";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function newCameraSource(settings: OrgSettings): CameraSource {
  return {
    id: `draft-${crypto.randomUUID()}`,
    name: "New Camera Source",
    url: "",
    source_type: "rtsp",
    location_name: settings.default_location_name,
    latitude: settings.default_location_latitude,
    longitude: settings.default_location_longitude,
    model_profile: "fast",
    enabled: true,
  };
}

function isPersistedCamera(id: string) {
  return UUID_RE.test(id);
}

function cameraFromApi(camera: CameraInfo): CameraSource {
  return {
    id: camera.id,
    name: camera.name,
    url: camera.source_url ?? "",
    source_type: (camera.source_type as SourceType) ?? "http_snapshot",
    location_name: camera.location_name ?? "",
    latitude: camera.latitude != null ? String(camera.latitude) : "",
    longitude: camera.longitude != null ? String(camera.longitude) : "",
    model_profile: camera.model_profile ?? "fast",
    enabled: camera.enabled ?? true,
  };
}

function cameraToPayload(camera: CameraSource) {
  return {
    name: camera.name.trim() || "New Camera Source",
    location_name: camera.location_name.trim() || undefined,
    latitude: camera.latitude ? parseFloat(camera.latitude) : undefined,
    longitude: camera.longitude ? parseFloat(camera.longitude) : undefined,
    source_type: camera.source_type,
    source_url: camera.url.trim() || undefined,
    model_profile: camera.model_profile,
    enabled: camera.enabled,
  };
}

function readCameraDrafts(): CameraSource[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CAMERA_DRAFT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persistCameraDrafts(cameras: CameraSource[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(CAMERA_DRAFT_KEY, JSON.stringify(cameras));
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [cameraDraftReady, setCameraDraftReady] = useState(false);
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dirtyCameraIds = useRef(new Set<string>());
  const savingCameraIds = useRef(new Set<string>());

  const [settings, setSettings] = useState<OrgSettings>(() => {
    const defaults: OrgSettings = {
      default_model_profile: "fast",
      confidence_threshold: "0.35",
      review_threshold: "0.6",
      preprocessing_mode: "auto",
      enable_plate_recognition: true,
      enable_helmet_detection: true,
      enable_seatbelt_detection: true,
      evidence_retention_days: "90",
      default_location_name: "Bengaluru Traffic Demo Zone",
      default_location_latitude: "12.9716",
      default_location_longitude: "77.5946",
    };

    if (typeof window === "undefined") return defaults;

    try {
      const raw = localStorage.getItem(ORG_SETTINGS_KEY);
      if (!raw) return defaults;
      const saved = JSON.parse(raw);
      return saved.settings ? { ...defaults, ...saved.settings } : defaults;
    } catch {
      return defaults;
    }
  });

  const [cameras, setCameras] = useState<CameraSource[]>(readCameraDrafts);

  const persistCameraSource = useCallback(async (camera: CameraSource, options?: { silent?: boolean }) => {
    if (savingCameraIds.current.has(camera.id)) return;
    savingCameraIds.current.add(camera.id);

    try {
      const payload = cameraToPayload(camera);
      let createdCameraId: string | null = null;
      let shouldResaveCreatedCamera = false;

      if (isPersistedCamera(camera.id)) {
        const updated = await updateCamera(camera.id, payload);
        const nextCamera = cameraFromApi(updated);
        setCameras((prev) => {
          const next = prev.map((cam) => (cam.id === camera.id ? nextCamera : cam));
          persistCameraDrafts(next);
          return next;
        });
      } else {
        const created = await createCamera(payload);
        createdCameraId = created.id;
        setCameras((prev) => {
          const latestDraft = prev.find((cam) => cam.id === camera.id);
          const nextCamera = latestDraft ? { ...latestDraft, id: created.id } : cameraFromApi(created);
          shouldResaveCreatedCamera = Boolean(
            latestDraft && JSON.stringify(cameraToPayload(latestDraft)) !== JSON.stringify(payload),
          );
          const next = prev.map((cam) => (cam.id === camera.id ? nextCamera : cam));
          persistCameraDrafts(next);
          return next;
        });
      }
      setSaveError(null);
      dirtyCameraIds.current.delete(camera.id);
      if (createdCameraId && shouldResaveCreatedCamera) {
        dirtyCameraIds.current.add(createdCameraId);
      }
    } catch (error) {
      if (!options?.silent) {
        setSaveError(error instanceof Error ? error.message : "Failed to save camera source.");
      }
    } finally {
      savingCameraIds.current.delete(camera.id);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (!user) return;
    const drafts = readCameraDrafts();

    fetchCameras()
      .then((apiCameras) => {
        const draftById = new Map(drafts.map((camera) => [camera.id, camera]));
        const apiSources = apiCameras.map((camera) => {
          const mapped = cameraFromApi(camera);
          return draftById.get(mapped.id) ?? mapped;
        });
        const unsavedDrafts = drafts.filter((camera) => !isPersistedCamera(camera.id));
        const next = [...unsavedDrafts, ...apiSources];
        setCameras(next);
        persistCameraDrafts(next);
      })
      .catch(() => {
        // Drafts already keep local camera sources available if the API is down.
      })
      .finally(() => {
        setCameraDraftReady(true);
      });
  }, [user]);

  useEffect(() => {
    if (!cameraDraftReady) return;

    persistCameraDrafts(cameras);
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);

    autosaveTimer.current = setTimeout(() => {
      cameras.forEach((camera) => {
        if (dirtyCameraIds.current.has(camera.id) && (camera.name.trim() || camera.url.trim())) {
          void persistCameraSource(camera, { silent: true });
        }
      });
    }, 800);

    return () => {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    };
  }, [cameraDraftReady, cameras, persistCameraSource]);

  function updateSetting<K extends keyof OrgSettings>(key: K, value: OrgSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function addCamera() {
    const newCam = newCameraSource(settings);
    setCameras((prev) => {
      const next = [...prev, newCam];
      persistCameraDrafts(next);
      return next;
    });
    setSaved(false);
    setSaveError(null);
    dirtyCameraIds.current.add(newCam.id);
    void persistCameraSource(newCam);
  }

  function updateCameraLocal(id: string, patch: Partial<CameraSource>) {
    setCameras((prev) => {
      const next = prev.map((c) => (c.id === id ? { ...c, ...patch } : c));
      persistCameraDrafts(next);
      return next;
    });
    setSaved(false);
    dirtyCameraIds.current.add(id);
  }

  function removeCamera(id: string) {
    setCameras((prev) => {
      const next = prev.filter((c) => c.id !== id);
      persistCameraDrafts(next);
      return next;
    });
    setSaved(false);
    setSaveError(null);
    dirtyCameraIds.current.delete(id);
    if (isPersistedCamera(id)) {
      void deleteCamera(id).catch((error) => {
        setSaveError(error instanceof Error ? error.message : "Failed to delete camera source.");
      });
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setSaveError(null);
    try {
      localStorage.setItem(ORG_SETTINGS_KEY, JSON.stringify({ settings }));

      for (const cam of cameras) {
        await persistCameraSource(cam);
      }

      setSaved(true);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  const roleMeta = ROLE_LABELS[user?.role ?? ""] ?? ROLE_LABELS.viewer;

  if (authLoading || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center px-5 py-6 text-slate-100">
        <Loader2 className="size-6 animate-spin text-violet-300" />
      </main>
    );
  }

  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">
              Settings
            </h1>
            <p className="mt-2 text-slate-400">
              Your profile, organization config, camera sources, and detection policies.
            </p>
          </div>
          <Button
            onClick={handleSave}
            disabled={saving}
            className="cursor-pointer bg-violet-300 text-slate-950 hover:bg-violet-200"
          >
            {saving ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : <Save className="mr-1.5 size-3.5" />}
            Save Settings
          </Button>
        </header>

        {saved && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-lime-400/20 bg-lime-400/10 p-3 text-sm text-lime-200"
          >
            Settings saved successfully.
          </motion.div>
        )}

        {saveError && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200"
          >
            {saveError}
          </motion.div>
        )}

        <Card className="border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
                <User className="size-5 text-slate-400" />
              </div>
              <div>
                <CardTitle className="text-lg text-white">Your Profile</CardTitle>
                <p className="text-xs text-slate-500">Account details and organization membership</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="flex items-center gap-2">
                  <User className="size-4 text-slate-500" />
                  <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Name</span>
                </div>
                <p className="text-sm font-medium text-white">{user.full_name}</p>
              </div>
              <div className="space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="flex items-center gap-2">
                  <Mail className="size-4 text-slate-500" />
                  <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Email</span>
                </div>
                <p className="text-sm font-medium text-white">{user.email}</p>
              </div>
              <div className="space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="flex items-center gap-2">
                  <Shield className="size-4 text-slate-500" />
                  <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Role</span>
                </div>
                <Badge className={roleMeta.color}>{roleMeta.label}</Badge>
              </div>
              <div className="space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-slate-500" />
                  <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Organization</span>
                </div>
                <p className="text-sm font-medium text-white">{user.org_name}</p>
                <p className="font-mono text-[10px] text-slate-600">{user.org_id}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <div>
                <p className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                  Organization Default Location
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  Used as the fallback map center and as the default location for new camera sources.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Location Name
                  </label>
                  <Input
                    value={settings.default_location_name}
                    onChange={(e) => updateSetting("default_location_name", e.target.value)}
                    placeholder="e.g. Bengaluru Traffic Demo Zone"
                    className="h-9 bg-white/5 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Latitude
                  </label>
                  <Input
                    type="number"
                    step="any"
                    value={settings.default_location_latitude}
                    onChange={(e) => updateSetting("default_location_latitude", e.target.value)}
                    placeholder="12.9716"
                    className="h-9 bg-white/5 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Longitude
                  </label>
                  <Input
                    type="number"
                    step="any"
                    value={settings.default_location_longitude}
                    onChange={(e) => updateSetting("default_location_longitude", e.target.value)}
                    placeholder="77.5946"
                    className="h-9 bg-white/5 text-sm"
                  />
                </div>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <KeyRound className="size-4 text-slate-500" />
              <div className="flex-1">
                <p className="text-sm text-slate-300">Password</p>
                <p className="text-xs text-slate-600">Change your account password</p>
              </div>
              <Button variant="outline" size="sm" className="cursor-pointer text-xs">
                Change Password
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
                <Settings2 className="size-5 text-slate-400" />
              </div>
              <div>
                <CardTitle className="text-lg text-white">Detection Policy</CardTitle>
                <p className="text-xs text-slate-500">
                  {user.org_name} &middot; Model profiles, thresholds, and detection modules
                </p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                  Default Model Profile
                </label>
                <div className="space-y-2">
                  {MODEL_PROFILES.map((profile) => (
                    <button
                      key={profile.value}
                      type="button"
                      onClick={() => updateSetting("default_model_profile", profile.value)}
                      className={`flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-colors ${
                        settings.default_model_profile === profile.value
                          ? "border-violet-300/30 bg-violet-300/10"
                          : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]"
                      }`}
                    >
                      <Cpu className={`mt-0.5 size-4 shrink-0 ${
                        settings.default_model_profile === profile.value ? "text-violet-300" : "text-slate-500"
                      }`} />
                      <div>
                        <p className={`text-sm font-medium ${
                          settings.default_model_profile === profile.value ? "text-violet-200" : "text-slate-300"
                        }`}>
                          {profile.label}
                        </p>
                        <p className="text-xs text-slate-500">{profile.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                    Confidence Threshold
                  </label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={settings.confidence_threshold}
                    onChange={(e) => updateSetting("confidence_threshold", e.target.value)}
                    className="h-11 border-white/[0.06] bg-white/[0.03]"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                    Review Threshold
                  </label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={settings.review_threshold}
                    onChange={(e) => updateSetting("review_threshold", e.target.value)}
                    className="h-11 border-white/[0.06] bg-white/[0.03]"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                    Evidence Retention (days)
                  </label>
                  <Input
                    type="number"
                    min="1"
                    value={settings.evidence_retention_days}
                    onChange={(e) => updateSetting("evidence_retention_days", e.target.value)}
                    className="h-11 border-white/[0.06] bg-white/[0.03]"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                Detection Modules
              </label>
              <div className="grid gap-2 sm:grid-cols-3">
                {[
                  { key: "enable_plate_recognition" as const, label: "Plate Recognition" },
                  { key: "enable_helmet_detection" as const, label: "Helmet Detection" },
                  { key: "enable_seatbelt_detection" as const, label: "Seatbelt Detection" },
                ].map((mod) => (
                  <button
                    key={mod.key}
                    type="button"
                    onClick={() => updateSetting(mod.key, !settings[mod.key])}
                    className={`flex items-center gap-2 rounded-xl border p-3 text-left transition-colors ${
                      settings[mod.key]
                        ? "border-lime-300/30 bg-lime-300/10"
                        : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]"
                    }`}
                  >
                    <Shield className={`size-4 ${settings[mod.key] ? "text-lime-300" : "text-slate-500"}`} />
                    <span className={`text-sm ${settings[mod.key] ? "text-lime-200" : "text-slate-400"}`}>
                      {mod.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="grid size-10 place-items-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
                  <Camera className="size-5 text-slate-400" />
                </div>
                <div>
                  <CardTitle className="text-lg text-white">Camera Sources</CardTitle>
                  <p className="text-xs text-slate-500">
                    Configure CCTV endpoints, RTSP streams, or file watchers per location. Sources autosave as you edit.
                  </p>
                </div>
              </div>
              <Button
                onClick={addCamera}
                variant="outline"
                className="cursor-pointer"
              >
                <Plus className="mr-1.5 size-3.5" /> Add Source
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {cameras.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.02] py-12">
                <Signal className="mb-3 size-8 text-slate-600" />
                <p className="text-sm text-slate-400">No camera sources configured.</p>
                <p className="mt-1 text-xs text-slate-600">
                  Add HTTP snapshot URLs, RTSP streams, or file watcher paths.
                </p>
              </div>
            ) : (
              cameras.map((cam) => {
                const sourceMeta = SOURCE_TYPE_LABELS[cam.source_type];
                const SourceIcon = sourceMeta.icon;
                return (
                  <div
                    key={cam.id}
                    className="space-y-3 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <SourceIcon className="size-4 text-slate-500" />
                        <Badge variant="outline" className="border-white/[0.08] text-slate-400">
                          {sourceMeta.label}
                        </Badge>
                        {cam.enabled ? (
                          <Badge className="bg-lime-300/15 text-lime-300">Active</Badge>
                        ) : (
                          <Badge className="bg-slate-300/10 text-slate-500">Disabled</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => updateCameraLocal(cam.id, { enabled: !cam.enabled })}
                          className={`rounded-lg border px-2 py-1 text-xs transition-colors ${
                            cam.enabled
                              ? "border-lime-300/30 bg-lime-300/10 text-lime-300"
                              : "border-white/[0.06] bg-white/[0.03] text-slate-500"
                          }`}
                        >
                          {cam.enabled ? "On" : "Off"}
                        </button>
                        <button
                          type="button"
                          onClick={() => removeCamera(cam.id)}
                          className="grid size-7 place-items-center rounded-lg border border-white/[0.06] bg-white/[0.03] text-slate-500 transition-colors hover:border-red-300/30 hover:bg-red-300/10 hover:text-red-300"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                          Camera Name
                        </label>
                        <Input
                          value={cam.name}
                          onChange={(e) => updateCameraLocal(cam.id, { name: e.target.value })}
                          placeholder="e.g. MG Road Cam 2"
                          className="h-9 bg-white/5 text-sm"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                          Source Type
                        </label>
                        <div className="flex gap-1.5">
                          {(Object.keys(SOURCE_TYPE_LABELS) as SourceType[]).map((st) => (
                            <button
                              key={st}
                              type="button"
                              onClick={() => updateCameraLocal(cam.id, { source_type: st })}
                              className={`flex-1 rounded-lg border px-2 py-1.5 text-[10px] uppercase tracking-[0.12em] transition-colors ${
                                cam.source_type === st
                                  ? "border-violet-300/30 bg-violet-300/10 text-violet-200"
                                  : "border-white/[0.06] bg-white/[0.03] text-slate-500 hover:text-slate-300"
                              }`}
                            >
                              {SOURCE_TYPE_LABELS[st].label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                        {cam.source_type === "rtsp" ? "RTSP URL" : cam.source_type === "file_watcher" ? "Watch Directory" : "HTTP Snapshot URL"}
                      </label>
                      <Input
                        value={cam.url}
                        onChange={(e) => updateCameraLocal(cam.id, { url: e.target.value })}
                        placeholder={
                          cam.source_type === "rtsp"
                            ? "rtsp://192.168.1.100:554/stream1"
                            : cam.source_type === "file_watcher"
                              ? "/data/cctv-inbox/camera-01/"
                              : "http://cctv-server/snapshot.jpg"
                        }
                        className="h-9 bg-white/5 text-sm"
                      />
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                      <div className="space-y-1.5">
                        <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                          Location
                        </label>
                        <Input
                          value={cam.location_name}
                          onChange={(e) => updateCameraLocal(cam.id, { location_name: e.target.value })}
                          placeholder="e.g. MG Road Junction"
                          className="h-9 bg-white/5 text-sm"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                          Latitude
                        </label>
                        <Input
                          type="number"
                          step="any"
                          value={cam.latitude}
                          onChange={(e) => updateCameraLocal(cam.id, { latitude: e.target.value })}
                          placeholder="12.9756"
                          className="h-9 bg-white/5 text-sm"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                          Longitude
                        </label>
                        <Input
                          type="number"
                          step="any"
                          value={cam.longitude}
                          onChange={(e) => updateCameraLocal(cam.id, { longitude: e.target.value })}
                          placeholder="77.6068"
                          className="h-9 bg-white/5 text-sm"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                        Model Profile Override
                      </label>
                      <div className="flex gap-1.5">
                        {MODEL_PROFILES.map((profile) => (
                          <button
                            key={profile.value}
                            type="button"
                            onClick={() => updateCameraLocal(cam.id, { model_profile: profile.value })}
                            className={`flex-1 rounded-lg border px-2 py-1.5 text-[10px] uppercase tracking-[0.12em] transition-colors ${
                              cam.model_profile === profile.value
                                ? "border-violet-300/30 bg-violet-300/10 text-violet-200"
                                : "border-white/[0.06] bg-white/[0.03] text-slate-500 hover:text-slate-300"
                            }`}
                          >
                            {profile.label.split(" ")[0]}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-xl border border-white/[0.06] bg-white/[0.03]">
                <Cpu className="size-5 text-slate-400" />
              </div>
              <div>
                <CardTitle className="text-lg text-white">Runtime Artifacts</CardTitle>
                <p className="text-xs text-slate-500">Pretrained model weights and export status</p>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                { name: "Fast Vehicle (YOLO11-S)", file: "UVH-26-MV-YOLOv11-S.pt", status: "ready" },
                { name: "Accuracy Vehicle (RT-DETRv2)", file: "best.pth", status: "needs_export" },
                { name: "Review Vehicle (D-FINE)", file: "best_stg1.pth", status: "needs_export" },
                { name: "Helmet Detection (YOLO11)", file: "yolov11s(80 epochs).pt", status: "ready" },
              ].map((model) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-200">{model.name}</p>
                    <p className="font-mono text-[10px] text-slate-600">{model.file}</p>
                  </div>
                  <Badge
                    className={
                      model.status === "ready"
                        ? "bg-lime-300/15 text-lime-300"
                        : "bg-amber-300/15 text-amber-300"
                    }
                  >
                    {model.status === "ready" ? "Ready" : "Needs Export"}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
