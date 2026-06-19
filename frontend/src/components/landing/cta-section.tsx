"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";

export function CTASection() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-12 sm:px-8">
      <div className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-gradient-to-br from-cyan-400/[0.06] to-transparent p-8 text-center sm:p-12">
        <span className="font-metadata text-xs uppercase tracking-widest text-cyan-400/70">
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
            href="/process"
            className="group inline-flex h-11 items-center justify-center rounded-lg bg-cyan-400 px-6 text-sm font-medium text-[#0a0c0a] transition-all hover:bg-cyan-300 hover:shadow-[0_8px_24px_rgba(34,211,238,0.2)]"
          >
            Process evidence
            <ArrowRight className="ml-2 size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </Link>
          <Link
            href="/analytics"
            className="inline-flex h-11 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] px-6 text-sm font-medium transition-colors hover:bg-white/[0.06]"
          >
            View analytics
          </Link>
        </div>
      </div>
    </section>
  );
}
