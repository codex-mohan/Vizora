"use client";

import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  Camera,
  Car,
  CheckCircle2,
  Eye,
  FileCheck2,
  Fingerprint,
  HardHat,
  MapPin,
  RadioTower,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Users,
} from "lucide-react";
import { motion } from "motion/react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0 },
};

export function FeaturesSection() {
  return (
    <section className="py-12 sm:py-20" id="features">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-10 flex flex-col gap-4 sm:mb-16 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="font-metadata text-xs tracking-wider text-slate-500">
              Platform Features
            </span>
            <h2 className="mt-3 max-w-lg font-heading text-3xl font-bold leading-tight tracking-tight text-white sm:mt-4 sm:text-4xl md:text-5xl">
              What Vizora does
            </h2>
          </div>
          <p className="max-w-xs text-sm text-slate-400">
            Not a model demo. A complete evidence workflow for traffic enforcement.
          </p>
        </div>

        <div className="mb-4 grid gap-4 sm:mb-6 sm:gap-6 md:grid-cols-3">
          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="group h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-violet-400/20 hover:shadow-lg hover:shadow-violet-400/5 sm:p-6">
              <div className="mb-5 flex items-start justify-between sm:mb-6">
                <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                  Detection
                </span>
                <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                  YOLO11s
                </span>
              </div>
              <div className="mb-5 rounded-xl bg-white/[0.03] p-4 transition-colors duration-300 group-hover:bg-white/[0.05] sm:mb-6">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 rounded-lg border border-white/[0.06] bg-[#111318] px-3 py-1.5">
                    <Camera className="size-4 text-violet-400" />
                    <span className="font-metadata text-[10px] text-slate-400">Input</span>
                  </div>
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                    <div className="h-full w-4/5 rounded-full bg-violet-400 transition-all duration-500 group-hover:w-full" />
                  </div>
                  <span className="font-metadata text-xs text-violet-400">5 objects</span>
                </div>
              </div>
              <h3 className="mb-2 text-base font-semibold text-white sm:text-lg">
                Vehicle & Road User Detection
              </h3>
              <p className="text-sm text-slate-400">
                YOLO11 localizes vehicles, riders, pedestrians, plates, and headwear classes with bounding boxes and confidence scores.
              </p>
            </div>
          </motion.div>

          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="group h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-amber-400/20 hover:shadow-lg hover:shadow-amber-400/5 sm:p-6">
              <div className="mb-5 flex items-start justify-between sm:mb-6">
                <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                  OCR
                </span>
                <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                  PP-OCRv5
                </span>
              </div>
              <div className="mb-5 rounded-xl bg-white/[0.03] p-3 transition-colors duration-300 group-hover:bg-white/[0.05] sm:mb-6 sm:p-4">
                <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
                  {["KA01", "AB", "1234"].map((chunk) => (
                    <div
                      key={chunk}
                      className="rounded-lg border border-white/[0.06] bg-[#111318] p-2 text-center transition-all duration-300 group-hover:scale-[1.02]"
                    >
                      <span className="font-metadata text-sm text-amber-400">{chunk}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-2 flex justify-end">
                  <span className="rounded bg-amber-400/10 px-2 py-0.5 font-metadata text-[10px] text-amber-400">
                    97% conf
                  </span>
                </div>
              </div>
              <h3 className="mb-2 text-base font-semibold text-white sm:text-lg">
                License Plate Recognition
              </h3>
              <p className="text-sm text-slate-400">
                Two-stage pipeline: vehicle crop + PaddleOCR. Regional language support. PARSeq fallback for dirty plates.
              </p>
            </div>
          </motion.div>

          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0.3, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="group h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-violet-400/20 hover:shadow-lg hover:shadow-violet-400/5 sm:p-6">
              <div className="mb-5 flex items-start justify-between sm:mb-6">
                <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                  Evidence
                </span>
                <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                  SHA-256
                </span>
              </div>
              <div className="mb-5 flex items-center justify-center rounded-xl bg-white/[0.03] p-4 transition-colors duration-300 group-hover:bg-white/[0.05] sm:mb-6">
                <div className="relative">
                  <div className="flex size-16 items-center justify-center rounded-full border-2 border-violet-400/30 transition-all duration-500 group-hover:border-violet-400/60 group-hover:shadow-lg group-hover:shadow-violet-400/20">
                    <Shield className="size-6 text-violet-400 transition-transform duration-300 group-hover:scale-110" />
                  </div>
                  <div className="absolute -right-1 -bottom-1 flex size-6 items-center justify-center rounded-full bg-lime-400 transition-transform duration-300 group-hover:scale-110">
                    <CheckCircle2 className="size-3 text-[#100f18]" />
                  </div>
                </div>
              </div>
              <h3 className="mb-2 text-base font-semibold text-white sm:text-lg">
                Tamper-Evident Packets
              </h3>
              <p className="text-sm text-slate-400">
                Hash-chained evidence with annotated frames, OCR result, VLM description, and calibrated confidence.
              </p>
            </div>
          </motion.div>
        </div>

        <div className="mb-4 grid gap-4 sm:mb-6 sm:gap-6 md:grid-cols-2">
          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0.1, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-lime-400/20 hover:shadow-lg hover:shadow-lime-400/5 sm:p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:gap-6">
                <div className="flex shrink-0 items-center justify-center rounded-xl bg-white/[0.03] p-4 transition-colors duration-300 group-hover:bg-white/[0.05] sm:w-auto">
                  <div className="relative flex size-16 items-center justify-center rounded-full border-2 border-lime-400/30 transition-all duration-500 group-hover:border-lime-400/60 sm:size-20">
                    <RadioTower className="size-6 text-lime-400 transition-transform duration-300 group-hover:scale-110 sm:size-8" />
                  </div>
                </div>
                <div className="flex-1">
                  <div className="mb-2 flex items-start justify-between">
                    <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                      Realtime
                    </span>
                  </div>
                  <h3 className="mb-1 text-xl font-semibold text-white sm:text-2xl">
                    Live Camera Event Feed
                  </h3>
                  <p className="text-sm text-slate-400">
                    SSE-powered realtime feed. New violations appear as they are processed. Camera-level preprocessing state machine ensures consistent tracking.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0.25, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-amber-400/20 hover:shadow-lg hover:shadow-amber-400/5 sm:p-6">
              <div className="flex flex-col-reverse gap-4 sm:flex-row sm:gap-6">
                <div className="flex-1">
                  <div className="mb-2 flex items-start justify-between">
                    <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                      Configurable
                    </span>
                  </div>
                  <h3 className="mb-1 text-xl font-semibold text-white sm:text-2xl">
                    Pydantic Model Registry
                  </h3>
                  <p className="text-sm text-slate-400">
                    Switch between fast, accuracy, and review profiles. YOLO11s handles fast detection; RT-DETRv2 powers the accuracy profile.
                  </p>
                </div>
                <div className="flex shrink-0 items-center justify-center rounded-xl bg-white/[0.03] p-4 transition-colors duration-300 group-hover:bg-white/[0.05] sm:w-auto">
                  <div className="flex gap-1">
                    {["Y", "O", "L", "O"].map((num, i) => (
                      <div
                        className="flex size-8 items-center justify-center rounded border border-white/[0.06] bg-[#111318] transition-all duration-300 group-hover:-translate-y-0.5 group-hover:shadow-sm"
                        key={i}
                        style={{ transitionDelay: `${i * 50}ms` }}
                      >
                        <span className="font-metadata text-sm text-violet-400">{num}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        <motion.div
          initial="hidden"
          transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
          variants={fadeUp}
          viewport={{ once: true, margin: "-50px" }}
          whileInView="visible"
        >
          <div className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:shadow-lg hover:shadow-violet-400/5 sm:p-6">
            <div className="mb-5 flex items-start justify-between sm:mb-6">
              <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                Violation Coverage
              </span>
              <span className="font-metadata text-[10px] uppercase tracking-wider text-slate-500 sm:text-xs">
                7 Types
              </span>
            </div>

            <div className="mb-6 grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-3 text-xl font-semibold text-white sm:text-2xl">
                  Every violation type, automated.
                </h3>
                <p className="mb-4 text-sm text-slate-400">
                  From single-frame helmet checks to temporal wrong-side trajectory analysis. Each type has specialized detection logic.
                </p>
                <div className="flex flex-wrap gap-2">
                  {["Helmet", "Seatbelt", "Triple Ride", "Wrong Side", "Stop Line", "Red Light", "Illegal Parking"].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/[0.06] bg-white/[0.03] px-3 py-1 font-metadata text-[10px] transition-colors duration-300 hover:bg-violet-400/10 hover:text-violet-400"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 transition-all duration-300 group-hover:bg-white/[0.05]">
                    <span className="font-metadata text-[10px] text-slate-500">Single-frame</span>
                    <p className="mt-1 font-metadata text-lg text-violet-400">2 types</p>
                  </div>
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] p-3 transition-all duration-300 group-hover:bg-white/[0.05]">
                    <span className="font-metadata text-[10px] text-slate-500">Temporal</span>
                    <p className="mt-1 font-metadata text-lg text-amber-400">5 types</p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Temporal violations require track history. Still-image inputs degrade gracefully with lower confidence.
                </p>
              </div>

              <div className="rounded-xl bg-white/[0.03] p-4 transition-colors duration-300 group-hover:bg-white/[0.05]">
                <div className="mb-3 flex items-center gap-2">
                  <div className="flex size-8 items-center justify-center rounded-full bg-violet-400/10">
                    <Eye className="size-4 text-violet-400" />
                  </div>
                  <span className="font-metadata text-xs text-slate-500">
                    Live Detection Feed
                  </span>
                </div>
                <div className="mb-4 space-y-2 rounded-lg border border-white/[0.06] bg-[#111318] p-3">
                  {[
                    { icon: HardHat, label: "Helmet", conf: "94%", color: "text-red-400" },
                    { icon: Users, label: "Triple Ride", conf: "87%", color: "text-yellow-400" },
                    { icon: Siren, label: "Red Light", conf: "76%", color: "text-rose-400" },
                    { icon: ShieldAlert, label: "Seatbelt", conf: "91%", color: "text-orange-400" },
                  ].map((item) => {
                    const Icon = item.icon;
                    return (
                      <div key={item.label} className="flex items-center gap-2">
                        <Icon className={`size-3 ${item.color}`} />
                        <span className="text-[10px] text-slate-400">{item.label}</span>
                        <span className={`ml-auto font-metadata text-[10px] ${item.color}`}>{item.conf}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-[#111318] p-3">
                  <div>
                    <span className="font-metadata text-[10px] text-slate-500">Review Status</span>
                    <p className="font-metadata text-xs text-lime-400">Auto-approved</p>
                  </div>
                  <div className="flex size-6 items-center justify-center rounded-full bg-lime-400/20">
                    <CheckCircle2 className="size-3 text-lime-400" />
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
