"use client";

import { CTASection } from "@/components/landing/cta-section";
import { EvidenceSection } from "@/components/landing/evidence-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { Footer } from "@/components/landing/footer";
import { HeroSection } from "@/components/landing/hero-section";
import { ModelsSection } from "@/components/landing/models-section";
import { WorkflowSection } from "@/components/landing/workflow-section";
import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0c0a] text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#0a0c0a]/80 backdrop-blur-2xl">
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="group flex items-center gap-2.5">
            <div className="grid size-9 place-items-center rounded-lg bg-cyan-400/10 text-cyan-400 transition-colors group-hover:bg-cyan-400/15">
              <ShieldCheck className="size-4.5" />
            </div>
            <span className="font-heading text-lg font-semibold tracking-tight">
              Vizora
            </span>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {[
              { href: "#features", label: "Features" },
              { href: "#workflow", label: "How it works" },
              { href: "#models", label: "Models" },
              { href: "#evidence", label: "Evidence" },
              { href: "/analytics", label: "Analytics" },
              { href: "/cameras", label: "Cameras" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-white"
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/violations"
              className="hidden rounded-lg px-3 py-1.5 text-sm text-slate-400 transition-colors hover:text-white sm:inline"
            >
              Records
            </Link>
            <Link
              href="/process"
              className="inline-flex h-9 items-center rounded-lg bg-cyan-400 px-4 text-sm font-medium text-[#0a0c0a] transition-all hover:bg-cyan-300 hover:shadow-[0_8px_24px_rgba(34,211,238,0.2)]"
            >
              Process <ArrowRight className="ml-1.5 size-3.5" />
            </Link>
          </div>
        </nav>
      </header>

      <HeroSection />
      <FeaturesSection />
      <WorkflowSection />
      <ModelsSection />
      <EvidenceSection />
      <CTASection />
      <Footer />
    </main>
  );
}
