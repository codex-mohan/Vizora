import { ArrowLeft, BrainCircuit, Camera, ShieldCheck, ShieldX } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const sampleEvidence = {
  id: "ev-sample-001",
  request_id: "req-sample-001",
  camera_id: "MG Road Cam 1",
  timestamp: "2026-06-18T17:42:11Z",
  violation_type: "HELMET",
  confidence: 0.94,
  plate: "KA01AB1234",
  vehicle_class: "motorcycle",
  model_profile: "mvp",
  detections: [
    { label: "motorcycle", confidence: 0.96, bbox: { x1: 120, y1: 180, x2: 380, y2: 420 } },
    { label: "rider", confidence: 0.94, bbox: { x1: 180, y1: 100, x2: 320, y2: 300 } },
    { label: "rider", confidence: 0.89, bbox: { x1: 200, y1: 120, x2: 340, y2: 320 } },
  ],
  plates: [
    { text: "KA01AB1234", confidence: 0.97 },
  ],
  description: "At 2026-06-18 17:42:11 UTC, camera MG Road Cam 1 captured an image with 3 detected objects (1 motorcycle, 2 riders). Plate candidates: KA01AB1234. Violations: Rider detected without helmet compliance (confidence 94%). Evidence quality score: 87%. Human review not required. Evidence packet: ev-sample-001.",
  hash_chain: "sha256:a1b2c3d4e5f6...",
  review_required: false,
  quality_score: 0.87,
};

export default function EvidencePage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex items-center gap-4">
          <Link href="/violations" className="inline-flex h-8 cursor-pointer items-center justify-center rounded-lg border border-white/15 bg-white/[0.03] px-3 text-sm font-medium transition-colors hover:bg-white/[0.08]">
            <ArrowLeft className="mr-1 size-3.5" /> Back
          </Link>
          <div>
            <h1 className="font-heading text-3xl font-semibold tracking-[-0.04em] text-white">Evidence Viewer</h1>
            <p className="mt-1 font-metadata text-sm text-slate-500">Packet {params.id}</p>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
          <div className="space-y-6">
            <Card className="overflow-hidden border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 font-heading text-2xl">
                  <Camera className="size-5 text-cyan-300" /> Annotated Evidence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-black/50">
                  <div className="flex min-h-[400px] items-center justify-center text-center text-slate-500">
                    <div>
                      <Camera className="mx-auto mb-4 size-10" />
                      <p>Annotated evidence frames will appear here.</p>
                      <p className="mt-2 text-xs text-slate-600">Upload and process an image to generate evidence.</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 font-heading text-2xl">
                  <BrainCircuit className="size-5 text-violet-300" /> Evidence Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-7 text-slate-200">{sampleEvidence.description}</p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Camera</p>
                    <p className="mt-1 text-sm text-white">{sampleEvidence.camera_id}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Time</p>
                    <p className="mt-1 text-sm text-white">{sampleEvidence.timestamp.replace("T", " ").replace("Z", "")}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Plate</p>
                    <p className="mt-1 font-metadata text-sm text-cyan-200">{sampleEvidence.plate}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Vehicle</p>
                    <p className="mt-1 text-sm text-white capitalize">{sampleEvidence.vehicle_class}</p>
                  </div>
                  <div className="col-span-2 rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Violation</p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant="outline" className="border-red-400/30 text-red-200">{sampleEvidence.violation_type}</Badge>
                      <span className="font-metadata text-xs text-slate-400">{Math.round(sampleEvidence.confidence * 100)}%</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="font-heading text-xl">OCR Results</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {sampleEvidence.plates.map((plate, i) => (
                  <div key={i} className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.06] p-3">
                    <p className="font-metadata text-lg text-amber-100">{plate.text}</p>
                    <p className="mt-1 text-xs text-slate-500">confidence {Math.round(plate.confidence * 100)}%</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Verification</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-3 rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.06] p-3">
                  {sampleEvidence.review_required ? <ShieldX className="size-5 text-amber-300" /> : <ShieldCheck className="size-5 text-emerald-300" />}
                  <div>
                    <p className="text-sm font-medium text-white">{sampleEvidence.review_required ? "Review Required" : "Auto Approved"}</p>
                    <p className="text-xs text-slate-500">Quality score {Math.round(sampleEvidence.quality_score * 100)}%</p>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Hash Chain</p>
                  <p className="mt-1 break-all font-metadata text-xs text-violet-200">{sampleEvidence.hash_chain}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}
