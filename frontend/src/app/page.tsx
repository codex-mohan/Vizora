"use client";

import { useState } from "react";
import { CTASection } from "@/components/landing/cta-section";
import { EvidenceSection } from "@/components/landing/evidence-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { Footer } from "@/components/landing/footer";
import { HeroSection } from "@/components/landing/hero-section";
import { ModelsSection } from "@/components/landing/models-section";
import { StatsSection } from "@/components/landing/stats-section";
import { WorkflowSection } from "@/components/landing/workflow-section";
import { ArrowRight, Menu, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { href: "#features", label: "Features" },
  { href: "#workflow", label: "How it works" },
  { href: "#models", label: "Models" },
  { href: "#evidence", label: "Evidence" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function Home() {
  const [mobileNav, setMobileNav] = useState(false);
  const { user, logout, loading } = useAuth();

  return (
    <main className="min-h-screen bg-[#100f18] text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#100f18]/80 backdrop-blur-2xl">
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="group flex items-center gap-2.5">
            <div className="grid size-9 place-items-center rounded-lg bg-violet-400/10 text-violet-400 transition-colors group-hover:bg-violet-400/15">
              <ShieldCheck className="size-4.5" />
            </div>
            <span className="font-heading text-lg font-semibold tracking-tight">
              Vizora
            </span>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => (
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
            {loading ? null : user ? (
              <>
                <Link
                  href="/dashboard"
                  className="inline-flex h-9 items-center rounded-lg bg-violet-400 px-4 text-sm font-medium text-[#100f18] transition-all hover:bg-violet-300 hover:shadow-[0_8px_24px_rgba(167,139,250,0.2)]"
                >
                  Dashboard <ArrowRight className="ml-1.5 size-3.5" />
                </Link>
                <button onClick={logout} className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition-colors hover:text-white">Sign out</button>
              </>
            ) : (
              <>
                <Link href="/login" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 transition-colors hover:text-white">Sign in</Link>
                <Link href="/signup" className="inline-flex h-9 items-center rounded-lg bg-violet-400 px-4 text-sm font-medium text-[#100f18] transition-all hover:bg-violet-300">Get started</Link>
              </>
            )}
            <button
              onClick={() => setMobileNav(!mobileNav)}
              className="grid size-9 place-items-center rounded-lg transition-colors hover:bg-white/[0.06] md:hidden"
            >
              {mobileNav ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </nav>

        {mobileNav && (
          <div className="border-t border-white/[0.06] bg-[#100f18]/95 backdrop-blur-2xl md:hidden">
            <div className="space-y-1 px-5 py-4">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileNav(false)}
                  className="block rounded-lg px-3 py-2.5 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-white"
                >
                  {item.label}
                </Link>
              ))}
              {user ? (
                <Link
                  href="/dashboard"
                  onClick={() => setMobileNav(false)}
                  className="block rounded-lg px-3 py-2.5 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-white"
                >
                  Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    href="/login"
                    onClick={() => setMobileNav(false)}
                    className="block rounded-lg px-3 py-2.5 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-white"
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/signup"
                    onClick={() => setMobileNav(false)}
                    className="block rounded-lg px-3 py-2.5 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-white"
                  >
                    Get started
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      <HeroSection />
      <StatsSection />
      <FeaturesSection />
      <WorkflowSection />
      <ModelsSection />
      <EvidenceSection />
      <CTASection />
      <Footer />
    </main>
  );
}
