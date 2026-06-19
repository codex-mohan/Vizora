"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSearch2,
  Filter,
  Search,
  X,
} from "lucide-react";

import { fetchViolations } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { ViolationListItem, ViolationListResponse } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

const VIOLATION_TYPES = [
  "HELMET",
  "SEATBELT",
  "TRIPLE_RIDE",
  "WRONG_SIDE",
  "STOP_LINE",
  "RED_LIGHT",
  "ILLEGAL_PARKING",
] as const;

const TYPE_BADGE_CLASS: Record<string, string> = {
  HELMET: "text-red-400 bg-red-400/10",
  SEATBELT: "text-orange-400 bg-orange-400/10",
  TRIPLE_RIDE: "text-amber-400 bg-amber-400/10",
  WRONG_SIDE: "text-rose-400 bg-rose-400/10",
  STOP_LINE: "text-pink-400 bg-pink-400/10",
  RED_LIGHT: "text-red-500 bg-red-500/10",
  ILLEGAL_PARKING: "text-yellow-400 bg-yellow-400/10",
};

const STATUS_BADGE_CLASS: Record<string, string> = {
  approved: "text-lime-400 bg-lime-400/10",
  pending: "text-amber-400 bg-amber-400/10",
  rejected: "text-red-400 bg-red-400/10",
  escalated: "text-rose-400 bg-rose-400/10",
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 90
      ? "bg-lime-400"
      : pct >= 75
        ? "bg-violet-400"
        : pct >= 60
          ? "bg-amber-400"
          : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-metadata text-xs text-slate-300">{pct}%</span>
    </div>
  );
}

function TableSkeleton() {
  return (
    <TableBody>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i} className="border-white/5">
          <TableCell><Skeleton className="h-5 w-20" /></TableCell>
          <TableCell><Skeleton className="h-5 w-24" /></TableCell>
          <TableCell><Skeleton className="h-5 w-28" /></TableCell>
          <TableCell><Skeleton className="h-5 w-32" /></TableCell>
          <TableCell><Skeleton className="h-5 w-20" /></TableCell>
          <TableCell><Skeleton className="h-5 w-16" /></TableCell>
          <TableCell><Skeleton className="h-5 w-16" /></TableCell>
          <TableCell><Skeleton className="h-5 w-20" /></TableCell>
        </TableRow>
      ))}
    </TableBody>
  );
}

function exportCsv(items: ViolationListItem[]) {
  const header = [
    "id",
    "violation_type",
    "confidence",
    "camera_id",
    "location",
    "plate",
    "timestamp",
    "status",
    "review_required",
  ];
  const rows = items.map((v) => [
    v.id,
    v.violation_type,
    String(v.confidence),
    v.camera_id,
    v.location,
    v.plate ?? "",
    v.timestamp,
    v.status ?? "pending",
    String(v.review_required),
  ]);
  const csv = [header.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "violations.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ViolationsPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [data, setData] = useState<ViolationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [violationType, setViolationType] = useState<string>("");
  const [plateSearch, setPlateSearch] = useState("");
  const [minConfidence, setMinConfidence] = useState<string>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [reviewOnly, setReviewOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

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
        const result = await fetchViolations({
          page,
          size,
          violation_type: violationType || undefined,
          plate_search: plateSearch || undefined,
          min_confidence: minConfidence ? Number(minConfidence) / 100 : undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          review_required: reviewOnly || undefined,
        });
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load violations");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [page, size, violationType, plateSearch, minConfidence, dateFrom, dateTo, reviewOnly]);

  const totalPages = data ? Math.ceil(data.total / size) : 0;

  function clearFilters() {
    setViolationType("");
    setPlateSearch("");
    setMinConfidence("");
    setDateFrom("");
    setDateTo("");
    setReviewOnly(false);
    setPage(1);
  }

  const hasActiveFilters =
    violationType || plateSearch || minConfidence || dateFrom || dateTo || reviewOnly;

  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">
              Violations
            </h1>
            <p className="mt-2 text-slate-400">Searchable record of all detected violations.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="cursor-pointer border-white/15 bg-white/[0.03]"
              onClick={() => exportCsv(data?.items ?? [])}
              disabled={!data?.items.length}
            >
              <Download className="mr-1.5 size-3.5" /> Export CSV
            </Button>
            <Link
              href="/process"
              className="inline-flex h-8 cursor-pointer items-center justify-center rounded-lg bg-violet-300 px-4 text-sm font-medium text-slate-950 transition-colors hover:bg-violet-200"
            >
              Process new <ArrowUpRight className="ml-1 size-3.5" />
            </Link>
          </div>
        </header>

        <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading text-2xl">
              All Violations
              {data ? (
                <span className="ml-3 text-base font-normal text-slate-500">
                  ({data.total.toLocaleString()})
                </span>
              ) : null}
            </CardTitle>
            <div className="flex items-center gap-2">
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="cursor-pointer text-slate-400"
                  onClick={clearFilters}
                >
                  <X className="mr-1 size-3.5" /> Clear
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer border-white/15 bg-white/[0.03]"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="mr-1.5 size-3.5" /> Filter
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {showFilters && (
              <div className="grid gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Violation Type
                  </label>
                  <Select value={violationType} onValueChange={(v) => { setViolationType(v ?? ""); setPage(1); }}>
                    <SelectTrigger className="h-9 w-full bg-white/5">
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      {VIOLATION_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t.replace(/_/g, " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Plate Search
                  </label>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-slate-500" />
                    <Input
                      value={plateSearch}
                      onChange={(e) => { setPlateSearch(e.target.value); setPage(1); }}
                      placeholder="e.g. KA01AB"
                      className="h-9 bg-white/5 pl-8"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Min Confidence (%)
                  </label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={minConfidence}
                    onChange={(e) => { setMinConfidence(e.target.value); setPage(1); }}
                    placeholder="0"
                    className="h-9 bg-white/5"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Review Required
                  </label>
                  <Button
                    variant={reviewOnly ? "default" : "outline"}
                    size="sm"
                    className={`w-full cursor-pointer ${reviewOnly ? "" : "border-white/15 bg-white/[0.03]"}`}
                    onClick={() => { setReviewOnly(!reviewOnly); setPage(1); }}
                  >
                    {reviewOnly ? "Review only" : "All"}
                  </Button>
                </div>

                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Date From
                  </label>
                  <Input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                    className="h-9 bg-white/5"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">
                    Date To
                  </label>
                  <Input
                    type="date"
                    value={dateTo}
                    onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                    className="h-9 bg-white/5"
                  />
                </div>
              </div>
            )}

            {error ? (
              <div className="rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">
                {error}
              </div>
            ) : null}

            <Table>
              <TableHeader>
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Time
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Type
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Camera
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Location
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Plate
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Confidence
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Status
                  </TableHead>
                  <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                    Review
                  </TableHead>
                </TableRow>
              </TableHeader>
              {loading ? (
                <TableSkeleton />
              ) : !data?.items.length ? (
                <TableBody>
                  <TableRow className="border-transparent hover:bg-transparent">
                    <TableCell colSpan={8}>
                      <div className="flex flex-col items-center justify-center py-16 text-slate-500">
                        <FileSearch2 className="mb-4 size-10" />
                        <p className="text-sm">No violations found.</p>
                        {hasActiveFilters && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="mt-2 cursor-pointer text-violet-300"
                            onClick={clearFilters}
                          >
                            Clear filters
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                </TableBody>
              ) : (
                <TableBody>
                  {data.items.map((v) => (
                    <TableRow
                      key={v.id}
                      className="cursor-pointer border-white/5 transition-colors hover:bg-white/[0.03]"
                      onClick={() => {
                        if (v.evidence_packet_id) {
                          router.push(`/evidence/${v.evidence_packet_id}`);
                        }
                      }}
                    >
                      <TableCell className="font-metadata text-xs text-slate-400">
                        {format(new Date(v.timestamp), "MMM d, HH:mm")}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={TYPE_BADGE_CLASS[v.violation_type] ?? ""}>
                          {v.violation_type.replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-slate-300">{v.camera_id}</TableCell>
                      <TableCell className="text-sm text-slate-400">{v.location}</TableCell>
                      <TableCell className="font-metadata text-sm text-violet-200">
                        {v.plate ?? "—"}
                      </TableCell>
                      <TableCell>
                        <ConfidenceBar value={v.confidence} />
                      </TableCell>
                      <TableCell>
                        <Badge className={STATUS_BADGE_CLASS[v.status ?? "pending"] ?? ""}>
                          {v.status ?? "pending"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {v.review_required ? (
                          <Badge variant="outline" className="border-amber-400/30 text-amber-200">
                            review
                          </Badge>
                        ) : (
                          <span className="text-xs text-slate-600">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              )}
            </Table>

            {data && totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="font-metadata text-xs text-slate-500">
                  Page {data.page} of {totalPages} &middot; {data.total.toLocaleString()} total
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="cursor-pointer border-white/15 bg-white/[0.03]"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    <ChevronLeft className="size-3.5" /> Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="cursor-pointer border-white/15 bg-white/[0.03]"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next <ChevronRight className="size-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
