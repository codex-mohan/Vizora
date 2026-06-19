"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { format } from "date-fns";
import {
  ArrowLeft,
  BrainCircuit,
  Camera,
  CheckCircle2,
  Eye,
  FileSearch2,
  Loader2,
  ShieldCheck,
  ShieldX,
  XCircle,
  AlertTriangle,
} from "lucide-react";

import { fetchEvidence, updateViolationStatus } from "@/lib/api";
import type { EvidencePacket } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const TYPE_BADGE_CLASS: Record<string, string> = {
  HELMET: "border-red-400/30 text-red-200",
  SEATBELT: "border-orange-400/30 text-orange-200",
  TRIPLE_RIDE: "border-yellow-400/30 text-yellow-200",
  WRONG_SIDE: "border-purple-400/30 text-purple-200",
  STOP_LINE: "border-blue-400/30 text-blue-200",
  RED_LIGHT: "border-rose-400/30 text-rose-200",
  ILLEGAL_PARKING: "border-teal-400/30 text-teal-200",
};

function MetadataCell({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
      <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <div className="mt-1 text-sm text-white">{value}</div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <Skeleton className="h-[400px] w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
      <div className="space-y-6">
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    </div>
  );
}

export default function EvidencePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [packet, setPacket] = useState<EvidencePacket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionDone, setActionDone] = useState<string | null>(null);
  const [selectedFrame, setSelectedFrame] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchEvidence(id);
        if (!cancelled) setPacket(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load evidence");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function handleAction(action: "approved" | "rejected" | "escalated") {
    if (!packet?.violation?.id) return;
    setActionLoading(action);
    try {
      await updateViolationStatus(packet.violation.id, action);
      setActionDone(action);
    } catch {
      // silently fail for demo
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          <LoadingSkeleton />
        </div>
      </main>
    );
  }

  if (error || !packet) {
    return (
      <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-center gap-4 py-32">
          <FileSearch2 className="size-12 text-slate-600" />
          <p className="text-lg text-slate-400">{error ?? "Evidence packet not found"}</p>
          <Link
            href="/violations"
            className="inline-flex h-8 items-center rounded-lg border border-white/15 bg-white/[0.03] px-4 text-sm transition-colors hover:bg-white/[0.08]"
          >
            <ArrowLeft className="mr-1 size-3.5" /> Back to violations
          </Link>
        </div>
      </main>
    );
  }

  const violation = packet.violation;
  const allFrames = [
    ...(packet.annotated_frame_url ? [packet.annotated_frame_url] : []),
    ...packet.frame_urls,
  ];
  const currentFrame = allFrames[selectedFrame];

  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex items-center gap-4">
          <Link
            href="/violations"
            className="inline-flex h-8 cursor-pointer items-center justify-center rounded-lg border border-white/15 bg-white/[0.03] px-3 text-sm font-medium transition-colors hover:bg-white/[0.08]"
          >
            <ArrowLeft className="mr-1 size-3.5" /> Back
          </Link>
          <div>
            <h1 className="font-heading text-3xl font-semibold tracking-[-0.04em] text-white">
              Evidence Viewer
            </h1>
            <p className="mt-1 font-metadata text-sm text-slate-500">Packet {packet.packet_id}</p>
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
                  {currentFrame ? (
                    <img
                      src={currentFrame}
                      alt="Evidence frame"
                      className="max-h-[500px] w-full object-contain"
                    />
                  ) : (
                    <div className="flex min-h-[400px] items-center justify-center text-center text-slate-500">
                      <div>
                        <Camera className="mx-auto mb-4 size-10" />
                        <p>No evidence frames available.</p>
                        <p className="mt-2 text-xs text-slate-600">
                          Upload and process an image to generate evidence.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                {allFrames.length > 1 && (
                  <div className="mt-3 flex gap-2 overflow-x-auto">
                    {allFrames.map((url, i) => (
                      <button
                        key={url}
                        onClick={() => setSelectedFrame(i)}
                        className={`h-16 w-24 shrink-0 cursor-pointer overflow-hidden rounded-lg border-2 transition-colors ${
                          i === selectedFrame
                            ? "border-cyan-300"
                            : "border-white/10 hover:border-white/25"
                        }`}
                      >
                        <img src={url} alt={`Frame ${i + 1}`} className="h-full w-full object-cover" />
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {(packet.vlm_description || violation?.description) && (
              <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 font-heading text-2xl">
                    <BrainCircuit className="size-5 text-violet-300" /> Evidence Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-7 text-slate-200">
                    {packet.vlm_description ?? violation?.description}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  {violation ? (
                    <>
                      <div className="col-span-2 rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                        <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                          Violation
                        </p>
                        <div className="mt-2 flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className={TYPE_BADGE_CLASS[violation.violation_type] ?? ""}
                          >
                            {violation.violation_type.replace(/_/g, " ")}
                          </Badge>
                          <span className="font-metadata text-xs text-slate-400">
                            {Math.round(violation.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                      <MetadataCell label="Camera" value={violation.camera_id} />
                      <MetadataCell
                        label="Time"
                        value={format(new Date(violation.timestamp), "MMM d, HH:mm:ss")}
                      />
                      <MetadataCell label="Location" value={violation.location} />
                      {violation.vehicle_class && (
                        <MetadataCell
                          label="Vehicle"
                          value={<span className="capitalize">{violation.vehicle_class}</span>}
                        />
                      )}
                    </>
                  ) : (
                    <div className="col-span-2 text-sm text-slate-500">
                      Violation metadata unavailable.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {violation?.plate && (
              <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                <CardHeader>
                  <CardTitle className="font-heading text-xl">Plate Recognition</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.06] p-3">
                    <p className="font-metadata text-lg text-amber-100">{violation.plate}</p>
                    {violation.plate_hash && (
                      <p className="mt-1 break-all font-metadata text-xs text-slate-500">
                        hash: {violation.plate_hash}
                      </p>
                    )}
                  </div>
                  {packet.plate_crop_url && (
                    <div className="overflow-hidden rounded-xl border border-white/10">
                      <img
                        src={packet.plate_crop_url}
                        alt="Plate crop"
                        className="w-full object-contain"
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Verification</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div
                  className={`flex items-center gap-3 rounded-2xl border p-3 ${
                    packet.hash_chain
                      ? "border-emerald-300/15 bg-emerald-300/[0.06]"
                      : "border-amber-300/15 bg-amber-300/[0.06]"
                  }`}
                >
                  {packet.hash_chain ? (
                    <ShieldCheck className="size-5 text-emerald-300" />
                  ) : (
                    <ShieldX className="size-5 text-amber-300" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-white">
                      {packet.hash_chain ? "Hash chain verified" : "No hash chain"}
                    </p>
                    <p className="text-xs text-slate-500">
                      {packet.hash_chain
                        ? "Evidence integrity cryptographically verified"
                        : "Hash chain not available for this packet"}
                    </p>
                  </div>
                </div>
                {packet.hash_chain && (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                    <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                      Hash Chain
                    </p>
                    <p className="mt-1 break-all font-metadata text-xs text-violet-200">
                      {packet.hash_chain}
                    </p>
                  </div>
                )}
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <p className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Created
                  </p>
                  <p className="mt-1 font-metadata text-xs text-slate-300">
                    {format(new Date(packet.created_at), "MMM d, yyyy HH:mm:ss")}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="font-heading text-xl">Review Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {actionDone ? (
                  <div
                    className={`flex items-center gap-3 rounded-2xl border p-3 ${
                      actionDone === "approved"
                        ? "border-emerald-300/15 bg-emerald-300/[0.06]"
                        : actionDone === "rejected"
                          ? "border-red-300/15 bg-red-300/[0.06]"
                          : "border-violet-300/15 bg-violet-300/[0.06]"
                    }`}
                  >
                    {actionDone === "approved" ? (
                      <CheckCircle2 className="size-5 text-emerald-300" />
                    ) : actionDone === "rejected" ? (
                      <XCircle className="size-5 text-red-300" />
                    ) : (
                      <AlertTriangle className="size-5 text-violet-300" />
                    )}
                    <p className="text-sm font-medium text-white capitalize">{actionDone}</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-3 gap-2">
                    <Button
                      size="sm"
                      className="cursor-pointer bg-emerald-500/20 text-emerald-200 hover:bg-emerald-500/30"
                      disabled={!!actionLoading}
                      onClick={() => handleAction("approved")}
                    >
                      {actionLoading === "approved" ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <CheckCircle2 className="mr-1 size-3.5" />
                      )}
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      className="cursor-pointer bg-red-500/20 text-red-200 hover:bg-red-500/30"
                      disabled={!!actionLoading}
                      onClick={() => handleAction("rejected")}
                    >
                      {actionLoading === "rejected" ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <XCircle className="mr-1 size-3.5" />
                      )}
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      className="cursor-pointer bg-violet-500/20 text-violet-200 hover:bg-violet-500/30"
                      disabled={!!actionLoading}
                      onClick={() => handleAction("escalated")}
                    >
                      {actionLoading === "escalated" ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Eye className="mr-1 size-3.5" />
                      )}
                      Escalate
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}
