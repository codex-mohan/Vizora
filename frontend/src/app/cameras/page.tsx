import { Camera, Signal, Wifi, WifiOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const cameras = [
  { id: "cam-001", name: "MG Road Cam 1", location: "MG Road Junction", lat: 12.9756, lng: 77.6068, mode: "CLEAN", status: "online", fps: 5, violations: 34 },
  { id: "cam-002", name: "NH-48 Junction", location: "NH-48 Toll Plaza", lat: 12.9100, lng: 77.6400, mode: "LOWLIGHT", status: "online", fps: 3, violations: 28 },
  { id: "cam-003", name: "Signal 12 Cross", location: "Signal 12", lat: 12.9500, lng: 77.6200, mode: "CLEAN", status: "online", fps: 5, violations: 22 },
  { id: "cam-004", name: "College Road", location: "College Road", lat: 12.9300, lng: 77.6100, mode: "RAIN", status: "online", fps: 4, violations: 19 },
  { id: "cam-005", name: "Market Road", location: "Market Road", lat: 12.9200, lng: 77.6300, mode: "CLEAN", status: "offline", fps: 0, violations: 15 },
  { id: "cam-006", name: "One-Way Street 7", location: "One-Way Street 7", lat: 12.9400, lng: 77.6500, mode: "HAZE", status: "online", fps: 4, violations: 12 },
  { id: "cam-007", name: "Toll Plaza A", location: "Toll Plaza A", lat: 12.9000, lng: 77.6600, mode: "CLEAN", status: "online", fps: 5, violations: 8 },
];

const modeColor: Record<string, string> = {
  CLEAN: "bg-emerald-300 text-slate-950",
  LOWLIGHT: "bg-amber-300 text-slate-950",
  HAZE: "bg-orange-300 text-slate-950",
  RAIN: "bg-blue-300 text-slate-950",
  MULTI: "bg-purple-300 text-slate-950",
};

export default function CamerasPage() {
  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header>
          <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">Cameras</h1>
          <p className="mt-2 text-slate-400">Camera status, preprocessing mode, and violation counts.</p>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cameras.map((cam) => (
            <Card key={cam.id} className="group border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl transition-colors hover:border-cyan-300/20">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="flex items-center gap-3">
                  <div className={`grid size-10 place-items-center rounded-full ${cam.status === "online" ? "bg-emerald-300/10" : "bg-red-300/10"}`}>
                    {cam.status === "online" ? <Wifi className="size-5 text-emerald-300" /> : <WifiOff className="size-5 text-red-300" />}
                  </div>
                  <div>
                    <CardTitle className="text-base font-medium text-white">{cam.name}</CardTitle>
                    <p className="font-metadata text-xs text-slate-500">{cam.id}</p>
                  </div>
                </div>
                <Badge className={modeColor[cam.mode] ?? ""}>{cam.mode}</Badge>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Camera className="size-3.5" />
                  <span>{cam.location}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Signal className="size-3.5" />
                  <span>{cam.lat.toFixed(4)}, {cam.lng.toFixed(4)}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">FPS</span>
                  <span className="font-heading text-2xl text-cyan-200">{cam.fps}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <span className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Violations</span>
                  <span className="font-heading text-2xl text-amber-200">{cam.violations}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}
