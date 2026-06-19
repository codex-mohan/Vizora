import { BarChart3, TrendingUp, Users, MapPin } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const violationTypeData = [
  { type: "Helmet", count: 45, color: "bg-red-400" },
  { type: "Triple Ride", count: 23, color: "bg-yellow-400" },
  { type: "Red Light", count: 18, color: "bg-rose-400" },
  { type: "Seatbelt", count: 15, color: "bg-orange-400" },
  { type: "Stop Line", count: 12, color: "bg-blue-400" },
  { type: "Illegal Parking", count: 9, color: "bg-teal-400" },
  { type: "Wrong Side", count: 6, color: "bg-purple-400" },
];

const hourlyData = [
  { hour: "6AM", count: 2 }, { hour: "7AM", count: 5 }, { hour: "8AM", count: 12 },
  { hour: "9AM", count: 18 }, { hour: "10AM", count: 14 }, { hour: "11AM", count: 10 },
  { hour: "12PM", count: 8 }, { hour: "1PM", count: 6 }, { hour: "2PM", count: 9 },
  { hour: "3PM", count: 11 }, { hour: "4PM", count: 15 }, { hour: "5PM", count: 20 },
  { hour: "6PM", count: 22 }, { hour: "7PM", count: 16 }, { hour: "8PM", count: 10 },
];

const hotspotLocations = [
  { name: "MG Road Junction", violations: 34, lat: 12.9756, lng: 77.6068 },
  { name: "NH-48 Toll Plaza", violations: 28, lat: 12.9100, lng: 77.6400 },
  { name: "Signal 12 Cross", violations: 22, lat: 12.9500, lng: 77.6200 },
  { name: "College Road", violations: 19, lat: 12.9300, lng: 77.6100 },
  { name: "Market Road", violations: 15, lat: 12.9200, lng: 77.6300 },
];

const repeatOffenders = [
  { plate: "KA01AB1234", count: 5, lastSeen: "2026-06-18 17:42:11" },
  { plate: "MH12CD5678", count: 3, lastSeen: "2026-06-18 17:38:05" },
  { plate: "DL03EF9012", count: 3, lastSeen: "2026-06-18 17:35:22" },
  { plate: "TN07GH3456", count: 2, lastSeen: "2026-06-18 17:30:14" },
];

const maxHourly = Math.max(...hourlyData.map(d => d.count));
const maxType = Math.max(...violationTypeData.map(d => d.count));

export default function AnalyticsPage() {
  return (
    <main className="min-h-screen px-5 py-6 text-slate-100 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header>
          <h1 className="font-heading text-4xl font-semibold tracking-[-0.04em] text-white">Analytics</h1>
          <p className="mt-2 text-slate-400">Violation trends, hotspots, and repeat offenders.</p>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Total Violations", value: "128", icon: BarChart3, tone: "text-cyan-200" },
            { label: "Active Cameras", value: "7", icon: MapPin, tone: "text-emerald-200" },
            { label: "Avg Confidence", value: "87%", icon: TrendingUp, tone: "text-amber-200" },
            { label: "Repeat Offenders", value: "12", icon: Users, tone: "text-violet-200" },
          ].map((metric) => {
            const Icon = metric.icon;
            return (
              <Card key={metric.label} className="border-white/10 bg-slate-950/55 shadow-xl shadow-black/20 backdrop-blur-xl">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <p className="font-metadata text-xs uppercase tracking-[0.22em] text-slate-500">{metric.label}</p>
                    <Icon className={`size-4 ${metric.tone}`} />
                  </div>
                  <p className={`mt-3 font-heading text-4xl ${metric.tone}`}>{metric.value}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Violations by Type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {violationTypeData.map((item) => (
                <div key={item.type} className="flex items-center gap-3">
                  <span className="w-24 text-sm text-slate-400">{item.type}</span>
                  <div className="flex-1 overflow-hidden rounded-full bg-white/5">
                    <div className={`h-2 rounded-full ${item.color}`} style={{ width: `${(item.count / maxType) * 100}%` }} />
                  </div>
                  <span className="w-8 text-right font-metadata text-sm text-slate-300">{item.count}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Time of Day Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-1.5" style={{ height: 200 }}>
                {hourlyData.map((item) => (
                  <div key={item.hour} className="flex flex-1 flex-col items-center gap-1">
                    <div className="w-full rounded-t-lg bg-cyan-400/80" style={{ height: `${(item.count / maxHourly) * 100}%` }} />
                    <span className="font-metadata text-[9px] text-slate-600">{item.hour}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Hotspot Locations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {hotspotLocations.map((loc, i) => (
                <div key={loc.name} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <div className="flex items-center gap-3">
                    <span className="grid size-8 place-items-center rounded-full bg-cyan-300/10 font-metadata text-sm text-cyan-200">{i + 1}</span>
                    <div>
                      <p className="text-sm font-medium text-white">{loc.name}</p>
                      <p className="font-metadata text-xs text-slate-500">{loc.lat.toFixed(4)}, {loc.lng.toFixed(4)}</p>
                    </div>
                  </div>
                  <span className="font-metadata text-lg text-cyan-200">{loc.violations}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="font-heading text-2xl">Repeat Offenders</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-left">
                      <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Plate</th>
                      <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Count</th>
                      <th className="pb-3 font-metadata text-xs uppercase tracking-[0.2em] text-slate-500">Last Seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {repeatOffenders.map((offender) => (
                      <tr key={offender.plate} className="border-b border-white/5">
                        <td className="py-3 font-metadata text-cyan-200">{offender.plate}</td>
                        <td className="py-3 font-metadata text-amber-200">{offender.count}</td>
                        <td className="py-3 font-metadata text-slate-500">{offender.lastSeen}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
