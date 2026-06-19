import Link from "next/link";
import { ArrowUpRight, Filter } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const sampleViolations = [
  { id: "v-001", type: "HELMET", camera: "MG Road Cam 1", plate: "KA01AB1234", confidence: 0.94, timestamp: "2026-06-18 17:42:11", status: "approved" },
  { id: "v-002", type: "TRIPLE_RIDE", camera: "NH-48 Junction", plate: "MH12CD5678", confidence: 0.87, timestamp: "2026-06-18 17:38:05", status: "review" },
  { id: "v-003", type: "RED_LIGHT", camera: "Signal 12 Cross", plate: "DL03EF9012", confidence: 0.76, timestamp: "2026-06-18 17:35:22", status: "review" },
  { id: "v-004", type: "SEATBELT", camera: "Toll Plaza A", plate: "TN07GH3456", confidence: 0.91, timestamp: "2026-06-18 17:30:14", status: "approved" },
  { id: "v-005", type: "ILLEGAL_PARKING", camera: "Market Road", plate: "KA05IJ7890", confidence: 0.82, timestamp: "2026-06-18 17:25:33", status: "rejected" },
  { id: "v-006", type: "WRONG_SIDE", camera: "One-Way Street 7", plate: "AP09KL1234", confidence: 0.69, timestamp: "2026-06-18 17:20:47", status: "review" },
  { id: "v-007", type: "STOP_LINE", camera: "Junction 14", plate: "GJ01MN5678", confidence: 0.88, timestamp: "2026-06-18 17:15:09", status: "approved" },
  { id: "v-008", type: "HELMET", camera: "College Road", plate: "RJ14OP9012", confidence: 0.96, timestamp: "2026-06-18 17:10:55", status: "approved" },
];

const statusColor: Record<string, string> = {
  approved: "bg-emerald-300 text-slate-950",
  review: "bg-amber-300 text-slate-950",
  rejected: "bg-red-300 text-slate-950",
};

const typeColor: Record<string, string> = {
  HELMET: "border-red-400/30 text-red-200",
  SEATBELT: "border-orange-400/30 text-orange-200",
  TRIPLE_RIDE: "border-yellow-400/30 text-yellow-200",
  WRONG_SIDE: "border-purple-400/30 text-purple-200",
  STOP_LINE: "border-blue-400/30 text-blue-200",
  RED_LIGHT: "border-rose-400/30 text-rose-200",
  ILLEGAL_PARKING: "border-teal-400/30 text-teal-200",
};

export default function ViolationsPage() {
  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">Violations</h1>
            <p className="mt-2 text-slate-400">Searchable record of all detected violations.</p>
          </div>
          <Link href="/process" className="inline-flex h-10 cursor-pointer items-center justify-center rounded-lg bg-cyan-300 px-5 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-200">
            Process new <ArrowUpRight className="ml-1 size-4" />
          </Link>
        </header>

        <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading text-2xl">All Violations</CardTitle>
            <Button variant="outline" size="sm" className="cursor-pointer border-white/15 bg-white/[0.03]">
              <Filter className="mr-2 size-3.5" /> Filter
            </Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left">
                    <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Type</th>
                    <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Camera</th>
                    <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Plate</th>
                    <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Confidence</th>
                    <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Time</th>
                    <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sampleViolations.map((v) => (
                    <tr key={v.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                      <td className="py-3">
                        <Badge variant="outline" className={typeColor[v.type] ?? ""}>{v.type}</Badge>
                      </td>
                      <td className="py-3 text-slate-300">{v.camera}</td>
                      <td className="py-3 font-metadata text-cyan-200">{v.plate}</td>
                      <td className="py-3 font-metadata text-slate-300">{Math.round(v.confidence * 100)}%</td>
                      <td className="py-3 font-metadata text-slate-500">{v.timestamp}</td>
                      <td className="py-3">
                        <Badge className={statusColor[v.status] ?? ""}>{v.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
