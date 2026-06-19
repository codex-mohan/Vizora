"use client";

import {
  BadgeCheck,
  CheckCircle2,
  Clock,
  Eye,
  FileCheck2,
  Shield,
  Timer,
} from "lucide-react";
import { motion } from "motion/react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0 },
};

export function EvidenceSection() {
  return (
    <section className="bg-white/[0.015] py-12 sm:py-20" id="evidence">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-10 flex flex-col gap-4 sm:mb-16 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="font-metadata text-xs tracking-wider text-slate-500">
              Evidence Generation
            </span>
            <h2 className="mt-3 max-w-lg font-heading text-3xl font-bold leading-tight tracking-tight text-white sm:mt-4 sm:text-4xl md:text-5xl">
              Court-ready, tamper-evident.
            </h2>
          </div>
          <p className="max-w-xs text-sm text-slate-400">
            Each violation generates a structured evidence packet with annotated frames, OCR, VLM description, and SHA-256 hash chain.
          </p>
        </div>

        <motion.div
          initial="hidden"
          transition={{ duration: 0.6, delay: 0, ease: "easeOut" }}
          variants={fadeUp}
          viewport={{ once: true, margin: "-50px" }}
          whileInView="visible"
        >
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 sm:p-6">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#111318] p-5">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Evidence Packet</span>
                  <span className="flex items-center gap-1.5">
                    <BadgeCheck className="size-3 text-emerald-400" /> Verified
                  </span>
                </div>
                <div className="mt-4 rounded-lg bg-white/[0.03] p-4">
                  <span className="text-[10px] uppercase tracking-widest text-slate-600">
                    Detected Event
                  </span>
                  <h3 className="mt-2 font-heading text-xl font-semibold text-white">
                    Helmet non-compliance
                  </h3>
                  <p className="mt-1 text-sm text-slate-400">
                    Motorcycle rider detected without helmet. Pose estimation confirms head-region exposure.
                  </p>
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    {[
                      ["Plate", "KA01AB1234"],
                      ["Camera", "MG Road"],
                      ["Confidence", "94%"],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg bg-white/[0.04] p-2.5">
                        <span className="text-[10px] uppercase tracking-widest text-slate-600">
                          {label}
                        </span>
                        <p className="mt-1 font-metadata text-sm font-medium text-white">
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                  <span className="text-[10px] uppercase tracking-widest text-slate-600">
                    Hash Chain
                  </span>
                  <p className="mt-1 break-all font-metadata text-[11px] text-violet-400">
                    sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6...
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="rounded-xl border border-white/[0.06] bg-[#111318] p-4">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Shield className="size-3.5 text-cyan-400" />
                    <span>VLM Summary</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    At 2026-06-18 17:42:11 UTC, camera MG Road captured an image with 3 detected objects (1 motorcycle, 2 riders). Plate candidates: KA01AB1234. Violations: Rider detected without helmet compliance (confidence 94%). Evidence quality score: 87%.
                  </p>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#111318] p-4">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Timer className="size-3.5 text-amber-400" />
                    <span>Review Status</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <CheckCircle2 className="size-4 text-emerald-400" />
                    <span className="text-sm text-emerald-400">Auto-approved</span>
                    <span className="text-xs text-slate-500">
                      — confidence above threshold
                    </span>
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#111318] p-4">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Clock className="size-3.5 text-violet-400" />
                    <span>Metadata</span>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-slate-500">Request ID:</span>{" "}
                      <span className="font-metadata text-slate-300">req-a1b2c3...</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Profile:</span>{" "}
                      <span className="font-metadata text-slate-300">mvp</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Mode:</span>{" "}
                      <span className="font-metadata text-slate-300">still_image</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Quality:</span>{" "}
                      <span className="font-metadata text-slate-300">87%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
