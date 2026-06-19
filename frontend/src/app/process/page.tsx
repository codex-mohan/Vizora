"use client";

import { Activity, AlertTriangle, BrainCircuit, Camera, FileImage, Loader2, ScanLine, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { processMedia } from "@/lib/api";
import type { DetectedObject, ProcessResult } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type ImageSize = {
  width: number;
  height: number;
};

function confidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function BoxOverlay({ detection, imageSize }: { detection: DetectedObject; imageSize: ImageSize | null }) {
  if (!imageSize) return null;

  const left = (detection.bbox.x1 / imageSize.width) * 100;
  const top = (detection.bbox.y1 / imageSize.height) * 100;
  const width = ((detection.bbox.x2 - detection.bbox.x1) / imageSize.width) * 100;
  const height = ((detection.bbox.y2 - detection.bbox.y1) / imageSize.height) * 100;

  return (
    <div
      className="absolute rounded-lg border border-violet-300/90 bg-violet-300/10 shadow-[0_0_28px_rgba(139,92,246,0.28)]"
      style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
    >
      <span className="absolute -top-7 left-0 rounded-md border border-violet-300/40 bg-slate-950/90 px-2 py-1 font-metadata text-[10px] uppercase tracking-[0.18em] text-violet-100 backdrop-blur">
        {detection.label} {confidence(detection.confidence)}
      </span>
    </div>
  );
}

export default function ProcessPage() {
  const [file, setFile] = useState<File | null>(null);
  const [cameraId, setCameraId] = useState("demo-camera");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<ImageSize | null>(null);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const imageRef = useRef<HTMLImageElement>(null);
  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  const topDetections = useMemo(() => result?.detections.slice(0, 6) ?? [], [result]);

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

  return (
    <main className="min-h-screen overflow-hidden px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex flex-col justify-between gap-5 rounded-[2rem] border border-white/10 bg-white/[0.04] p-5 shadow-2xl shadow-black/30 backdrop-blur-xl md:flex-row md:items-center">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet-300/20 bg-violet-300/10 px-3 py-1 font-metadata text-xs uppercase tracking-[0.24em] text-violet-200">
              <ScanLine className="size-3.5" /> Vizora Vision Workbench
            </div>
            <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white md:text-6xl">
              Evidence-first violation intelligence.
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-300">
              Upload a traffic image, run the live backend, inspect detections, OCR candidates, confidence, and review flags in one place.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 md:w-[360px]">
            <Card className="border-violet-300/15 bg-violet-300/[0.08]">
              <CardContent className="p-4">
                <p className="font-metadata text-xs uppercase tracking-[0.22em] text-violet-200">Detector</p>
                <p className="mt-2 font-heading text-2xl text-white">YOLO11n</p>
              </CardContent>
            </Card>
            <Card className="border-amber-300/15 bg-amber-300/[0.08]">
              <CardContent className="p-4">
                <p className="font-metadata text-xs uppercase tracking-[0.22em] text-amber-200">OCR</p>
                <p className="mt-2 font-heading text-2xl text-white">PP-OCRv5</p>
              </CardContent>
            </Card>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[420px_1fr]">
          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 font-heading text-2xl">
                <FileImage className="size-5 text-violet-300" /> Process Evidence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">Camera ID</label>
                <Input value={cameraId} onChange={(event) => setCameraId(event.target.value)} className="h-11 bg-white/5" />
              </div>
              <div className="space-y-2">
                <label className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">Traffic image</label>
                <Input
                  type="file"
                  accept="image/*"
                  className="h-11 cursor-pointer bg-white/5 file:text-violet-200"
                  onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
                />
              </div>
              <Button disabled={!file || loading} onClick={submit} className="h-12 w-full cursor-pointer bg-violet-300 text-slate-950 hover:bg-violet-200">
                {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Activity className="mr-2 size-4" />}
                Run live inference
              </Button>
              {error ? (
                <div className="rounded-2xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-100">
                  {error}
                </div>
              ) : null}
              {result ? (
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                    <p className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Objects</p>
                    <p className="mt-2 font-heading text-3xl">{result.detections.length}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                    <p className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">OCR</p>
                    <p className="mt-2 font-heading text-3xl">{result.plates.length}</p>
                  </div>
                  <div className="col-span-2 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                    <p className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Evidence packet</p>
                    <p className="mt-2 break-all font-metadata text-sm text-violet-100">{result.evidence_packet_id}</p>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="min-h-[620px] border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <CardTitle className="flex items-center gap-2 font-heading text-2xl">
                <Camera className="size-5 text-amber-300" /> Annotated Evidence
              </CardTitle>
              {result ? (
                <Badge className={result.review_required ? "bg-amber-300 text-slate-950" : "bg-lime-300 text-slate-950"}>
                  {result.review_required ? "Review required" : "Auto clear"}
                </Badge>
              ) : null}
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-black/50">
                {previewUrl ? (
                  <img
                    ref={imageRef}
                    src={previewUrl}
                    alt="Uploaded traffic evidence"
                    className="max-h-[560px] w-full object-contain"
                    onLoad={() => {
                      const image = imageRef.current;
                      if (image) setImageSize({ width: image.naturalWidth, height: image.naturalHeight });
                    }}
                  />
                ) : (
                  <div className="flex min-h-[420px] items-center justify-center text-center text-slate-500">
                    <div>
                      <FileImage className="mx-auto mb-4 size-10" />
                      Upload evidence to start inference.
                    </div>
                  </div>
                )}
                {previewUrl && topDetections.map((detection) => <BoxOverlay key={detection.id} detection={detection} imageSize={imageSize} />)}
              </div>

              {result ? (
                <div className="grid gap-4 xl:grid-cols-3">
                  <Card className="border-white/10 bg-white/[0.04] xl:col-span-2">
                    <CardHeader>
                      <CardTitle className="font-heading text-lg">Detections</CardTitle>
                    </CardHeader>
                    <CardContent className="grid gap-2 sm:grid-cols-2">
                      {topDetections.map((detection) => (
                        <div key={detection.id} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium capitalize">{detection.label}</span>
                            <span className="font-metadata text-xs text-violet-200">{confidence(detection.confidence)}</span>
                          </div>
                          <p className="mt-2 font-metadata text-xs text-slate-500">
                            {Math.round(detection.bbox.x1)}, {Math.round(detection.bbox.y1)} → {Math.round(detection.bbox.x2)}, {Math.round(detection.bbox.y2)}
                          </p>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                  <Card className="border-white/10 bg-white/[0.04]">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 font-heading text-lg">
                        <ShieldCheck className="size-4 text-amber-300" /> OCR Candidates
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {result.plates.length ? result.plates.map((plate, index) => (
                        <div key={`${plate.plate_text}-${index}`} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                          <p className="font-metadata text-sm text-amber-100">{plate.plate_text}</p>
                          <p className="mt-1 text-xs text-slate-500">confidence {confidence(plate.confidence)}</p>
                        </div>
                      )) : <p className="text-sm text-slate-500">No OCR candidates found.</p>}
                    </CardContent>
                  </Card>
                </div>
              ) : null}

              {result?.review_required ? (
                <div className="flex items-start gap-3 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-amber-100">
                  <AlertTriangle className="mt-0.5 size-5" />
                  <div>
                    <p className="font-medium">Human review recommended</p>
                    <p className="mt-1 text-sm text-amber-100/75">{result.review_reasons.join(", ") || "Low-confidence evidence requires reviewer confirmation."}</p>
                  </div>
                </div>
              ) : null}

              {result?.description ? (
                <Card className="border-violet-300/15 bg-violet-300/[0.06]">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 font-heading text-lg">
                      <BrainCircuit className="size-4 text-violet-300" /> Evidence Summary
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-6 text-slate-200">{result.description}</p>
                  </CardContent>
                </Card>
              ) : null}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
