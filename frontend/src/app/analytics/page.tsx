"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  BarChart3,
  Camera,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  fetchAnalyticsSummary,
  fetchDayHourHeatmap,
  fetchHotspotMap,
  fetchHotspots,
  fetchRepeatOffenders,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  AnalyticsSummary,
  HeatmapCell,
  Hotspot,
  HotspotMapResponse,
  RepeatOffender,
} from "@/lib/types";
import { ViolationHotspotMap } from "@/components/analytics/violation-hotspot-map";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PIE_COLORS = [
  "#f87171",
  "#fb923c",
  "#facc15",
  "#a78bfa",
  "#38bdf8",
  "#2dd4bf",
  "#e879f9",
];

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function KpiCard({
  label,
  value,
  icon: Icon,
  tone,
  loading,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  tone: string;
  loading: boolean;
}) {
  return (
    <Card className="border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <p className="font-metadata text-xs uppercase tracking-[0.22em] text-slate-500">
            {label}
          </p>
          <Icon className={`size-4 ${tone}`} />
        </div>
        {loading ? (
          <Skeleton className="mt-3 h-10 w-20" />
        ) : (
          <p className={`mt-3 font-heading text-4xl ${tone}`}>{value}</p>
        )}
      </CardContent>
    </Card>
  );
}

function SectionSkeleton({ height = 300 }: { height?: number }) {
  return <Skeleton className="w-full" style={{ height }} />;
}

export default function AnalyticsPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [hotspotMap, setHotspotMap] = useState<HotspotMapResponse | null>(null);
  const [offenders, setOffenders] = useState<RepeatOffender[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>([]);
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
        const authToken = token ?? undefined;
        const [s, h, o, hm, geo] = await Promise.all([
          fetchAnalyticsSummary({ token: authToken }),
          fetchHotspots(10, authToken),
          fetchRepeatOffenders(10, authToken),
          fetchDayHourHeatmap(authToken),
          fetchHotspotMap({ limit: 5000, token: authToken }),
        ]);
        if (!cancelled) {
          setSummary(s);
          setHotspots(h);
          setOffenders(o);
          setHeatmap(hm);
          setHotspotMap(geo);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const typeData = summary
    ? Object.entries(summary.by_type).map(([name, value]) => ({ name: name.replace(/_/g, " "), value }))
    : [];

  const hourData = summary
    ? Array.from({ length: 24 }, (_, i) => ({
        hour: `${i}:00`,
        count: summary.by_hour[String(i)] ?? 0,
      }))
    : [];

  const trendData = summary?.trend ?? [];

  const maxHeatmap = Math.max(...heatmap.map((c) => c.count), 1);

  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header>
          <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">
            Overview
          </h1>
          <p className="mt-2 text-slate-400">
            Live violation trends, hotspots, review load, and repeat offenders.
          </p>
        </header>

        {error && (
          <div className="rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Total Violations"
            value={summary?.total_violations.toLocaleString() ?? "—"}
            icon={BarChart3}
            tone="text-violet-200"
            loading={loading}
          />
          <KpiCard
            label="Violations Today"
            value={summary?.violations_today.toLocaleString() ?? "—"}
            icon={TrendingUp}
            tone="text-lime-200"
            loading={loading}
          />
          <KpiCard
            label="Avg Confidence"
            value={summary ? `${Math.round(summary.avg_confidence * 100)}%` : "—"}
            icon={CheckCircle2}
            tone="text-amber-200"
            loading={loading}
          />
          <KpiCard
            label="Active Cameras"
            value={summary?.active_cameras ?? "—"}
            icon={Camera}
            tone="text-violet-200"
            loading={loading}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <KpiCard
            label="Review Queue"
            value={summary?.review_queue_depth ?? "—"}
            icon={AlertTriangle}
            tone="text-rose-200"
            loading={loading}
          />
        </div>

        <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">Violation Road Heatmap</CardTitle>
            <p className="text-sm text-slate-400">
              Weighted violation density by location, with route-level overlays when road segment geometry is configured.
            </p>
          </CardHeader>
          <CardContent>
            <ViolationHotspotMap data={hotspotMap} loading={loading} />
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Violations by Type</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <SectionSkeleton />
              ) : typeData.length ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={typeData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={3}
                      dataKey="value"
                      stroke="none"
                    >
                      {typeData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: "#e2e8f0" }}
                    />
                    <Legend
                      formatter={(value: string) => (
                        <span className="text-xs text-slate-300">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-12 text-center text-sm text-slate-500">No data available.</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Time of Day</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <SectionSkeleton />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={hourData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis
                      dataKey="hour"
                      tick={{ fontSize: 10, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                      interval={2}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#64748b" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: "#e2e8f0" }}
                    />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <SectionSkeleton height={240} />
            ) : trendData.length ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "#64748b" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0f172a",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: "#e2e8f0" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ fill: "#8b5cf6", r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-12 text-center text-sm text-slate-500">No trend data available.</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">Day × Hour Heatmap</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <SectionSkeleton height={260} />
            ) : heatmap.length ? (
              <div className="overflow-x-auto">
                <div className="inline-grid gap-1" style={{ gridTemplateColumns: `auto repeat(24, minmax(28px, 1fr))` }}>
                  <div />
                  {Array.from({ length: 24 }).map((_, h) => (
                    <div
                      key={h}
                      className="text-center font-metadata text-[9px] text-slate-600"
                    >
                      {h}
                    </div>
                  ))}
                  {DAY_LABELS.map((day, d) => (
                    <React.Fragment key={d}>
                      <div className="flex items-center pr-2 font-metadata text-xs text-slate-500">
                        {day}
                      </div>
                      {Array.from({ length: 24 }).map((_, h) => {
                        const cell = heatmap.find((c) => c.day === d && c.hour === h);
                        const count = cell?.count ?? 0;
                        const intensity = count / maxHeatmap;
                        const bg =
                          count === 0
                            ? "bg-white/[0.03]"
                            : `rgba(139, 92, 246, ${0.1 + intensity * 0.7})`;
                        return (
                          <div
                            key={h}
                            className="aspect-square rounded-sm transition-colors"
                            style={{ backgroundColor: bg }}
                            title={`${day} ${h}:00 — ${count} violations`}
                          />
                        );
                      })}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            ) : (
              <p className="py-12 text-center text-sm text-slate-500">No heatmap data available.</p>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Hotspot Locations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? (
                <SectionSkeleton height={200} />
              ) : hotspots.length ? (
                hotspots.map((loc, i) => (
                  <div
                    key={loc.location_name}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="grid size-8 place-items-center rounded-full bg-violet-300/10 font-metadata text-sm text-violet-200">
                        {i + 1}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-white">{loc.location_name}</p>
                        {loc.latitude != null && loc.longitude != null && (
                          <p className="font-metadata text-xs text-slate-500">
                            {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}
                          </p>
                        )}
                      </div>
                    </div>
                    <span className="font-metadata text-lg text-violet-200">
                      {loc.violation_count}
                    </span>
                  </div>
                ))
              ) : (
                <p className="py-8 text-center text-sm text-slate-500">No hotspot data.</p>
              )}
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Repeat Offenders</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <SectionSkeleton height={200} />
              ) : offenders.length ? (
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/10 hover:bg-transparent">
                      <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                        Plate
                      </TableHead>
                      <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                        Count
                      </TableHead>
                      <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                        Last Seen
                      </TableHead>
                      <TableHead className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">
                        Types
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {offenders.map((o) => (
                      <TableRow key={o.plate_hash} className="border-white/5">
                        <TableCell className="font-metadata text-violet-200">
                          {o.plate_text}
                        </TableCell>
                        <TableCell className="font-metadata text-amber-200">
                          {o.violation_count}
                        </TableCell>
                        <TableCell className="font-metadata text-xs text-slate-500">
                          {o.last_seen_at
                            ? format(new Date(o.last_seen_at), "MMM d, HH:mm")
                            : "—"}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(o.violation_types)
                              .sort((a, b) => b[1] - a[1])
                              .slice(0, 3)
                              .map(([t, count]) => (
                                <Badge
                                  key={t}
                                  variant="outline"
                                  className="border-white/15 text-[10px] text-slate-400"
                                >
                                  {t.replace(/_/g, " ")} x{count}
                                </Badge>
                              ))}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="py-8 text-center text-sm text-slate-500">No repeat offenders.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
