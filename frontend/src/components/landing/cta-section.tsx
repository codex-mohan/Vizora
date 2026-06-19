"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";

export function CTASection() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-12 sm:px-8">
      <div className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-gradient-to-br from-violet-400/[0.06] to-transparent p-8 text-center sm:p-12">
        <div className="absolute inset-x-0 top-0 h-px animate-glow-line bg-gradient-to-r from-transparent via-violet-400/50 to-transparent" />
        <span className="font-metadata text-xs uppercase tracking-widest text-violet-400/70">
          Ready to Deploy
        </span>
        <h2 className="mx-auto mt-4 max-w-2xl font-heading text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Start processing traffic evidence now.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-base text-slate-400">
          Upload an image, run the pipeline, inspect detections, review OCR, and generate evidence packets — all from one interface.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/dashboard"
            className="animate-pulse-glow group inline-flex h-11 items-center justify-center rounded-lg bg-violet-400 px-6 text-sm font-medium text-[#100f18] transition-all hover:bg-violet-300 hover:shadow-[0_8px_24px_rgba(167,139,250,0.2)]"
          >
            Process evidence
            <ArrowRight className="ml-2 size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex h-11 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] px-6 text-sm font-medium transition-colors hover:bg-white/[0.06]"
          >
            View analytics
          </Link>
        </div>
      </div>
    </section>
  );
}
