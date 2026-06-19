"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, Gauge, ShieldCheck } from "lucide-react";
import { motion, useInView } from "motion/react";

function AnimatedCounter({ target, suffix = "", duration = 2 }: { target: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const increment = target / (duration * 60);
    const timer = setInterval(() => {
      start += increment;
      if (start >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, 1000 / 60);
    return () => clearInterval(timer);
  }, [inView, target, duration]);

  return (
    <span ref={ref} className="font-heading text-4xl font-bold text-white sm:text-5xl">
      {count.toLocaleString()}{suffix}
    </span>
  );
}

const stats = [
  { icon: ShieldCheck, label: "Violations Detected", target: 12847, suffix: "+", color: "text-violet-400", bg: "bg-violet-400/10" },
  { icon: Camera, label: "Cameras Supported", target: 500, suffix: "+", color: "text-lime-400", bg: "bg-lime-400/10" },
  { icon: CheckCircle2, label: "Detection Accuracy", target: 94, suffix: "%", color: "text-violet-400", bg: "bg-violet-400/10" },
  { icon: Gauge, label: "Avg Latency", target: 45, suffix: "ms", color: "text-amber-400", bg: "bg-amber-400/10" },
];

export function StatsSection() {
  return (
    <section className="relative border-y border-white/[0.04] bg-white/[0.01]">
      <div className="bg-dot-grid pointer-events-none absolute inset-0 opacity-30" />
      <div className="relative mx-auto max-w-7xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="grid grid-cols-2 gap-6 sm:gap-8 lg:grid-cols-4">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 24 }}
                transition={{ duration: 0.5, delay: i * 0.1, ease: "easeOut" }}
                viewport={{ once: true, margin: "-50px" }}
                whileInView={{ opacity: 1, y: 0 }}
                className="text-center"
              >
                <div className={`mx-auto mb-3 grid size-10 place-items-center rounded-lg ${stat.bg}`}>
                  <Icon className={`size-5 ${stat.color}`} />
                </div>
                <AnimatedCounter target={stat.target} suffix={stat.suffix} />
                <p className="mt-1 text-xs text-slate-500 sm:text-sm">{stat.label}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
