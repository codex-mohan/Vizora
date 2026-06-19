"use client";

import {
  Camera,
  CheckCircle2,
  Eye,
  Fingerprint,
  ScanLine,
  Search,
  Shield,
} from "lucide-react";
import { motion } from "motion/react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0 },
};

const steps = [
  {
    number: "01",
    title: "Capture",
    description: "Upload a traffic photo, batch of images, or short video burst. System auto-detects input type.",
    icon: Camera,
    visual: "camera",
  },
  {
    number: "02",
    title: "Preprocess",
    description: "Camera-level state machine applies classical or lightweight enhancement based on quality scoring.",
    icon: ScanLine,
    visual: "gauge",
  },
  {
    number: "03",
    title: "Detect",
    description: "YOLO11 localizes vehicles, riders, pedestrians. ByteTrack maintains persistent IDs for temporal logic.",
    icon: Search,
    visual: "bbox",
  },
  {
    number: "04",
    title: "Classify",
    description: "EfficientNetV2-S classifies helmet/seatbelt. PaddleOCR extracts plate text. RTMO estimates pose.",
    icon: Fingerprint,
    visual: "classify",
  },
  {
    number: "05",
    title: "Reason",
    description: "Rule engine evaluates 7 violation types using scene config, track history, and confidence fusion.",
    icon: Shield,
    visual: "rules",
  },
  {
    number: "06",
    title: "Evidence",
    description: "Generates annotated packet with hash chain, VLM description, and review flags for human approval.",
    icon: CheckCircle2,
    visual: "packet",
  },
];

export function WorkflowSection() {
  return (
    <section className="bg-white/[0.015] py-12 sm:py-20" id="workflow">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mb-10 flex flex-col gap-4 sm:mb-16 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="font-metadata text-xs tracking-wider text-slate-500">
              Pipeline Workflow · Configurable
            </span>
            <h2 className="mt-3 max-w-md font-heading text-3xl font-bold leading-tight tracking-tight text-white sm:mt-4 sm:text-4xl md:text-5xl">
              From image to evidence in six steps.
            </h2>
          </div>
          <p className="max-w-xs text-sm text-slate-400">
            Each stage is modular. The pipeline degrades gracefully when models are unavailable.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 md:gap-6">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <motion.div
                className="relative"
                initial="hidden"
                key={step.number}
                transition={{
                  duration: 0.6,
                  delay: index * 0.12,
                  ease: "easeOut",
                }}
                variants={fadeUp}
                viewport={{ once: true, margin: "-50px" }}
                whileInView="visible"
              >
                <div className="group h-full rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:-translate-y-1 hover:border-cyan-400/20 hover:shadow-lg hover:shadow-cyan-400/5 sm:p-6">
                  <div className="relative mb-5 flex aspect-[4/3] items-center justify-center overflow-hidden rounded-xl bg-white/[0.03] transition-colors duration-300 group-hover:bg-white/[0.05] sm:mb-6">
                    {step.visual === "camera" && (
                      <div className="relative">
                        <div className="rounded-lg border border-white/[0.06] bg-[#111318] p-4 shadow-sm transition-transform duration-300 group-hover:scale-105">
                          <Camera className="mx-auto size-8 text-cyan-400" />
                          <p className="mt-2 text-center font-metadata text-[10px] text-slate-500">
                            traffic_photo.jpg
                          </p>
                        </div>
                      </div>
                    )}
                    {step.visual === "gauge" && (
                      <div className="w-full px-6">
                        <div className="mb-2 flex justify-between font-metadata text-[10px] text-slate-500">
                          <span>Quality Score</span>
                          <span className="text-cyan-400">87%</span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
                          <div className="h-full w-[87%] animate-[expandWidth_1.5s_ease-out_0.3s_both] rounded-full bg-cyan-400" />
                        </div>
                        <div className="mt-3 grid grid-cols-3 gap-2">
                          {[
                            ["Bright", "OK"],
                            ["Blur", "Low"],
                            ["Haze", "None"],
                          ].map(([label, value]) => (
                            <div key={label} className="rounded bg-white/[0.04] p-1.5 text-center">
                              <p className="font-metadata text-[8px] text-slate-600">{label}</p>
                              <p className="font-metadata text-[10px] text-emerald-400">{value}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {step.visual === "bbox" && (
                      <div className="w-full px-4">
                        <div className="relative rounded-lg bg-[#111318] p-3">
                          <div className="h-20 w-full rounded bg-white/[0.04]" />
                          <div className="absolute left-6 top-5 h-12 w-16 rounded border-2 border-cyan-400/60">
                            <span className="absolute -top-4 left-0 font-metadata text-[8px] text-cyan-400">car 96%</span>
                          </div>
                          <div className="absolute left-14 top-8 h-8 w-10 rounded border-2 border-amber-400/60">
                            <span className="absolute -top-4 left-0 font-metadata text-[8px] text-amber-400">rider</span>
                          </div>
                        </div>
                      </div>
                    )}
                    {step.visual === "classify" && (
                      <div className="space-y-3 px-4">
                        <div className="flex items-center gap-3 rounded-lg border border-white/[0.06] bg-[#111318] p-2.5">
                          <div className="size-6 rounded bg-red-400/20" />
                          <span className="text-[10px] text-slate-400">No helmet detected</span>
                          <span className="ml-auto font-metadata text-[10px] text-red-400">94%</span>
                        </div>
                        <div className="flex items-center gap-3 rounded-lg border border-white/[0.06] bg-[#111318] p-2.5">
                          <div className="size-6 rounded bg-amber-400/20" />
                          <span className="text-[10px] text-slate-400">Plate: KA01AB1234</span>
                          <span className="ml-auto font-metadata text-[10px] text-amber-400">97%</span>
                        </div>
                      </div>
                    )}
                    {step.visual === "rules" && (
                      <div className="w-full px-4">
                        <div className="space-y-1.5">
                          {[
                            ["Helmet check", "FAIL"],
                            ["Triple ride", "PASS"],
                            ["Red light", "N/A"],
                          ].map(([rule, result]) => (
                            <div key={rule} className="flex items-center justify-between rounded bg-white/[0.04] px-3 py-1.5">
                              <span className="text-[10px] text-slate-400">{rule}</span>
                              <span className={`font-metadata text-[10px] ${result === "FAIL" ? "text-red-400" : result === "PASS" ? "text-emerald-400" : "text-slate-600"}`}>
                                {result}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {step.visual === "packet" && (
                      <div className="text-center">
                        <div className="inline-flex items-center gap-2 rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-4 py-2.5 transition-all duration-300 group-hover:bg-emerald-400/15 group-hover:shadow-md">
                          <CheckCircle2 className="size-4 text-emerald-400" />
                          <span className="font-metadata text-xs text-emerald-400">Evidence Ready</span>
                        </div>
                        <p className="mt-2 font-metadata text-[10px] text-slate-600">
                          ev-a1b2c3d4...
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="mb-2 flex items-start justify-between">
                    <span className="rounded-full bg-white/[0.06] px-2 py-0.5 font-metadata text-xs text-slate-400">
                      {step.number}
                    </span>
                    <Icon className="size-4 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                  </div>
                  <h3 className="mb-2 text-base font-medium text-white sm:text-lg">
                    {step.title}
                  </h3>
                  <p className="text-sm text-slate-400">
                    {step.description}
                  </p>
                </div>

                {index < steps.length - 1 && (
                  <div className="absolute top-1/2 -right-3 hidden w-6 border-t border-dashed border-white/10 md:block" />
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
