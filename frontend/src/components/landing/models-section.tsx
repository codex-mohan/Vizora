"use client";

import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Clock,
  Fingerprint,
  RadioTower,
} from "lucide-react";
import { motion } from "motion/react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0 },
};

const modelStack = [
  { stage: "Fast Detection", model: "YOLO11s ONNX/TRT", status: "active" },
  { stage: "Accuracy Detection", model: "RT-DETRv2", status: "ready" },
  { stage: "Tracking", model: "ByteTrack v2", status: "active" },
  { stage: "Helmet/Headwear", model: "Detector classes", status: "active" },
  { stage: "Seatbelt", model: "Detector classes", status: "review" },
  { stage: "Plate OCR", model: "PaddleOCR PP-OCRv5", status: "active" },
  { stage: "VLM", model: "Qwen-VL / template", status: "ready" },
];

const recentEvents = [
  { type: "HELMET", plate: "KA01AB1234", camera: "MG Road", confidence: 0.94, time: "2 min ago", status: "review" as const },
  { type: "TRIPLE_RIDE", plate: "MH12CD5678", camera: "NH-48 Junction", confidence: 0.87, time: "5 min ago", status: "approved" as const },
  { type: "RED_LIGHT", plate: "DL03EF9012", camera: "Signal 12", confidence: 0.76, time: "8 min ago", status: "review" as const },
  { type: "SEATBELT", plate: "TN07GH3456", camera: "Toll Plaza", confidence: 0.91, time: "12 min ago", status: "approved" as const },
];

const statusColor: Record<string, string> = {
  approved: "text-lime-400 bg-lime-400/10",
  review: "text-amber-400 bg-amber-400/10",
};

export function ModelsSection() {
  return (
    <section className="py-12 sm:py-20" id="models">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-10 flex flex-col gap-4 sm:mb-16 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="font-metadata text-xs tracking-wider text-slate-500">
              System Architecture
            </span>
            <h2 className="mt-3 max-w-lg font-heading text-3xl font-bold leading-tight tracking-tight text-white sm:mt-4 sm:text-4xl md:text-5xl">
              Models and realtime feed
            </h2>
          </div>
          <p className="max-w-xs text-sm text-slate-400">
            Pydantic-validated registry. Switch profiles without code changes.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 sm:p-6">
              <div className="flex items-center justify-between">
                <span className="font-metadata text-xs uppercase tracking-widest text-slate-500">
                  Model Registry
                </span>
                <Fingerprint className="size-4 text-slate-500" />
              </div>
              <p className="mt-4 text-sm text-slate-400">
                All models configurable via Pydantic profiles. Startup fails fast on unsupported choices.
              </p>

              <div className="mt-6 overflow-hidden rounded-xl border border-white/[0.06]">
                {modelStack.map((m, i) => (
                  <div
                    key={m.stage}
                    className={`flex items-center justify-between px-4 py-3 text-sm transition-colors hover:bg-white/[0.04] ${i % 2 === 0 ? "bg-white/[0.02]" : "bg-transparent"}`}
                  >
                    <span className="text-slate-500">{m.stage}</span>
                    <span className="font-medium text-white">{m.model}</span>
                    <span className="rounded-full bg-lime-400/10 px-2 py-0.5 text-xs text-lime-400">
                      {m.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          <motion.div
            initial="hidden"
            transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
            variants={fadeUp}
            viewport={{ once: true, margin: "-50px" }}
            whileInView="visible"
          >
            <div className="h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 sm:p-6">
              <div className="flex items-center justify-between">
                <span className="font-metadata text-xs uppercase tracking-widest text-slate-500">
                  Live Event Feed
                </span>
                <RadioTower className="size-4 text-slate-500" />
              </div>
              <p className="mt-4 text-sm text-slate-400">
                SSE-powered realtime feed. New violations appear as they are processed.
              </p>

              <div className="mt-6 space-y-2">
                {recentEvents.map((event, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 transition-colors hover:bg-white/[0.04]"
                  >
                    <div className={`grid size-8 place-items-center rounded-lg ${statusColor[event.status]?.split(" ")[1]}`}>
                      {event.status === "approved" ? (
                        <CheckCircle2 className="size-4 text-lime-400" />
                      ) : (
                        <AlertTriangle className="size-4 text-amber-400" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{event.type}</span>
                        <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${statusColor[event.status]}`}>
                          {event.status}
                        </span>
                      </div>
                      <p className="truncate text-xs text-slate-500">
                        {event.plate} · {event.camera}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="font-metadata text-xs text-violet-400">
                        {Math.round(event.confidence * 100)}%
                      </span>
                      <p className="text-[10px] text-slate-600">{event.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
