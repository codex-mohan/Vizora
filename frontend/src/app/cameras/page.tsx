"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  Camera,
  Loader2,
  Plus,
  Signal,
  Wifi,
  WifiOff,
} from "lucide-react";

import { createCamera, fetchCameras } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { CameraInfo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";

const MODE_BADGE_CLASS: Record<string, string> = {
  CLEAN: "text-lime-400 bg-lime-400/10",
  LOWLIGHT: "text-amber-400 bg-amber-400/10",
  HAZE: "text-orange-400 bg-orange-400/10",
  RAIN: "text-blue-400 bg-blue-400/10",
  MULTI: "text-violet-400 bg-violet-400/10",
};

function CameraCardSkeleton() {
  return (
    <Card className="border-white/10 bg-slate-950/55">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <Skeleton className="size-10 rounded-full" />
          <div className="space-y-1.5">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
        <Skeleton className="h-5 w-16 rounded-full" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-14 w-full rounded-2xl" />
      </CardContent>
    </Card>
  );
}

function AddCameraForm({ onCreated }: { onCreated: (cam: CameraInfo) => void }) {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const cam = await createCamera({
        name: name.trim(),
        location_name: location.trim() || undefined,
        latitude: lat ? parseFloat(lat) : undefined,
        longitude: lng ? parseFloat(lng) : undefined,
      });
      onCreated(cam);
      setOpen(false);
      setName("");
      setLocation("");
      setLat("");
      setLng("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create camera");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button className="cursor-pointer bg-violet-300 text-slate-950 hover:bg-violet-200">
            <Plus className="mr-1.5 size-3.5" /> Add Camera
          </Button>
        }
      />
      <SheetContent side="right">
        <form onSubmit={handleSubmit} className="flex h-full flex-col">
          <SheetHeader>
            <SheetTitle>Add Camera</SheetTitle>
            <SheetDescription>
              Register a new camera to the monitoring system.
            </SheetDescription>
          </SheetHeader>
          <div className="flex-1 space-y-4 p-4">
            <div className="space-y-1.5">
              <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                Name *
              </label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. MG Road Cam 2"
                className="bg-white/5"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                Location
              </label>
              <Input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. MG Road Junction"
                className="bg-white/5"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                  Latitude
                </label>
                <Input
                  type="number"
                  step="any"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  placeholder="12.9756"
                  className="bg-white/5"
                />
              </div>
              <div className="space-y-1.5">
                <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
                  Longitude
                </label>
                <Input
                  type="number"
                  step="any"
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                  placeholder="77.6068"
                  className="bg-white/5"
                />
              </div>
            </div>
            {error && (
              <div className="rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
                {error}
              </div>
            )}
          </div>
          <SheetFooter>
            <SheetClose
              render={
                <Button variant="outline" type="button" className="cursor-pointer">
                  Cancel
                </Button>
              }
            />
            <Button
              type="submit"
              disabled={!name.trim() || loading}
              className="cursor-pointer bg-violet-300 text-slate-950 hover:bg-violet-200"
            >
              {loading ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : null}
              Create
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}

export default function CamerasPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !token) router.push("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchCameras();
        if (!cancelled) setCameras(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load cameras");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleCreated(cam: CameraInfo) {
    setCameras((prev) => [cam, ...prev]);
  }

  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">
              Cameras
            </h1>
            <p className="mt-2 text-slate-400">
              Camera status, preprocessing mode, and violation counts.
            </p>
          </div>
          <AddCameraForm onCreated={handleCreated} />
        </header>

        {error && (
          <div className="rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <CameraCardSkeleton key={i} />
            ))}
          </div>
        ) : !cameras.length ? (
          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardContent className="flex flex-col items-center justify-center py-20">
              <Camera className="mb-4 size-12 text-slate-600" />
              <p className="text-lg text-slate-400">No cameras registered.</p>
              <p className="mt-2 text-sm text-slate-600">
                Add your first camera to start monitoring.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cameras.map((cam) => (
              <Card
                key={cam.id}
                className="group border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl transition-colors hover:border-violet-300/20"
              >
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <div className="flex items-center gap-3">
                    <div
                      className={`grid size-10 place-items-center rounded-full ${
                        cam.status === "online"
                          ? "bg-lime-300/10"
                          : "bg-red-300/10"
                      }`}
                    >
                      {cam.status === "online" ? (
                        <Wifi className="size-5 text-lime-300" />
                      ) : (
                        <WifiOff className="size-5 text-red-300" />
                      )}
                    </div>
                    <div>
                      <CardTitle className="text-base font-medium text-white">
                        {cam.name}
                      </CardTitle>
                      <p className="font-metadata text-xs text-slate-500">{cam.id}</p>
                    </div>
                  </div>
                  <Badge className={MODE_BADGE_CLASS[cam.current_mode] ?? ""}>
                    {cam.current_mode}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3">
                  {cam.location_name && (
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Camera className="size-3.5" />
                      <span>{cam.location_name}</span>
                    </div>
                  )}
                  {cam.latitude != null && cam.longitude != null && (
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Signal className="size-3.5" />
                      <span>
                        {cam.latitude.toFixed(4)}, {cam.longitude.toFixed(4)}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                      Status
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`size-2 rounded-full ${
                          cam.status === "online" ? "bg-lime-400" : "bg-red-400"
                        }`}
                      />
                      <span className="font-metadata text-sm capitalize text-slate-300">
                        {cam.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                      Created
                    </span>
                    <span className="font-metadata text-xs text-slate-400">
                      {format(new Date(cam.created_at), "MMM d, yyyy")}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
