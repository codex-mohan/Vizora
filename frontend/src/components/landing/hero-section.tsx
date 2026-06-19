"use client";

import { ArrowRight, BadgeCheck, Camera, ShieldCheck } from "lucide-react";
import Link from "next/link";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-5 pb-10 pt-10 sm:px-8 sm:pt-14">
        <div className="grid items-center gap-8 sm:gap-12 lg:grid-cols-2">
          <div className="space-y-6 animate-[fadeInUp_0.8s_ease-out_both]">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 font-metadata text-xs text-slate-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
              </span>
              <span>Automated Photo Enforcement System</span>
            </div>

            <h1 className="font-heading text-5xl font-bold leading-[1.05] tracking-tight text-white sm:text-6xl lg:text-7xl">
              Traffic violations,
              <br />
              detected from photos.
            </h1>

            <p className="max-w-lg text-base leading-7 text-slate-400 sm:text-lg">
              Vizora processes surveillance images, detects road users, identifies 7 violation types, reads license plates, and generates review-ready evidence packets.
            </p>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                href="/process"
                className="group inline-flex h-11 items-center gap-2 rounded-lg bg-cyan-400 px-6 text-sm font-medium text-[#0a0c0a] transition-all duration-300 hover:-translate-y-0.5 hover:bg-cyan-300 hover:shadow-[0_8px_24px_rgba(34,211,238,0.2)]"
              >
                Process evidence
                <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" />
              </Link>
              <Link
                href="/cameras"
                className="inline-flex h-11 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] px-6 text-sm font-medium transition-colors hover:bg-white/[0.06]"
              >
                View cameras
              </Link>
            </div>
          </div>

          <div className="relative hidden animate-[fadeInUp_0.8s_ease-out_0.2s_both] lg:block">
            <div className="relative rounded-2xl border border-white/[0.06] bg-[#111318] p-6">
              <div className="mb-4 flex justify-between font-metadata text-[10px] text-slate-500">
                <span>Evidence Packet — Live</span>
                <span className="flex items-center gap-1.5"><BadgeCheck className="size-3 text-emerald-400" /> Verified</span>
              </div>

              <div className="absolute top-20 -left-4 w-40 -rotate-2 animate-[float_6s_ease-in-out_infinite] rounded-xl border border-amber-400/20 bg-amber-400/[0.06] p-3 shadow-lg transition-transform duration-500 hover:rotate-0 hover:scale-105">
                <p className="font-metadata text-[10px] uppercase tracking-wider text-amber-400/70">
                  Violation Detected
                </p>
                <p className="mt-1 font-heading text-sm font-semibold text-white">
                  Helmet non-compliance
                </p>
                <p className="mt-1 text-[10px] text-slate-500">Confidence: 94%</p>
              </div>

              <div className="mx-auto my-6 max-w-sm rounded-xl bg-[#1a1d1a] p-5">
                <div className="mb-3 flex justify-between px-2 font-metadata text-[8px] text-slate-500">
                  <span>Detection Results</span>
                  <span className="flex items-center gap-1">
                    <Camera className="size-2.5" />
                    MG Road Cam 1
                  </span>
                </div>
                <div className="mb-3 px-2 font-metadata text-[10px] text-slate-400">
                  <p>motorcycle · rider · rider</p>
                  <p>plate: KA01AB1234</p>
                </div>
                <div className="rounded-lg bg-[#111318] p-3">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[8px] text-slate-400">motorcycle</span>
                      <span className="text-[8px] text-cyan-400">96%</span>
                    </div>
                    <div className="h-1 w-full overflow-hidden rounded-full bg-[#1a1d1a]">
                      <div className="h-full w-[96%] animate-[expandWidth_1.5s_ease-out_0.5s_both] rounded-full bg-cyan-400" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[8px] text-slate-400">rider</span>
                      <span className="text-[8px] text-cyan-400">94%</span>
                    </div>
                    <div className="h-1 w-full overflow-hidden rounded-full bg-[#1a1d1a]">
                      <div className="h-full w-[94%] animate-[expandWidth_1.5s_ease-out_0.7s_both] rounded-full bg-cyan-400" />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[8px] text-slate-400">plate OCR</span>
                      <span className="text-[8px] text-amber-400">97%</span>
                    </div>
                    <div className="h-1 w-full overflow-hidden rounded-full bg-[#1a1d1a]">
                      <div className="h-full w-[97%] animate-[expandWidth_1.5s_ease-out_0.9s_both] rounded-full bg-amber-400" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="absolute top-32 -right-2 animate-[float_6s_ease-in-out_1s_infinite] space-y-2">
                <div className="max-w-48 rounded-xl border border-white/[0.06] bg-[#111318] p-3 shadow-lg transition-transform duration-300 hover:scale-105">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="size-6 rounded-full bg-cyan-400/20" />
                    <span className="text-xs font-medium text-white">VLM Summary</span>
                    <span className="rounded-full bg-emerald-400/10 px-1.5 py-0.5 text-[8px] font-medium text-emerald-400">
                      Ready
                    </span>
                  </div>
                  <p className="text-[10px] leading-4 text-slate-400">
                    Motorcycle rider detected without helmet. Plate KA01AB1234 extracted. Evidence hash attached.
                  </p>
                </div>

                <div className="max-w-44 rounded-xl border border-white/[0.06] bg-[#111318] p-3 shadow-lg transition-transform duration-300 hover:scale-105">
                  <p className="font-metadata text-[10px] text-slate-500">
                    SHA-256:a1b2c3d4...
                  </p>
                  <p className="mt-1 text-[10px] text-emerald-400">Tamper-evident</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
