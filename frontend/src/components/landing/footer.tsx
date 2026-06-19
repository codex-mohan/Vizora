import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function Footer() {
  return (
    <footer className="relative overflow-hidden bg-[#080a08] pb-0">
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-80 bg-gradient-to-t from-violet-400/10 via-violet-400/5 to-transparent blur-3xl" />

      <div className="relative mx-auto max-w-7xl px-5 pt-12 sm:px-8">
        <div className="mb-10 flex flex-col items-center gap-4 sm:mb-16 sm:flex-row sm:justify-between">
          <Link
            className="font-metadata text-xs uppercase tracking-widest text-slate-500 transition-colors hover:text-white"
            href="/dashboard"
          >
            Process
          </Link>

          <div className="flex items-center gap-2.5">
            <div className="grid size-8 place-items-center rounded-lg bg-violet-400/10 text-violet-400">
              <ShieldCheck className="size-4" />
            </div>
            <span className="font-heading text-lg font-semibold tracking-tight text-white">Vizora</span>
          </div>

          <Link
            className="font-metadata text-xs uppercase tracking-widest text-slate-500 transition-colors hover:text-white"
            href="/dashboard"
          >
            Analytics
          </Link>
        </div>

        <h2 className="pb-1 text-center font-heading text-[14vw] font-bold leading-[0.85] tracking-tight text-white/[0.07] sm:text-[12vw]">
          VIZORA
        </h2>
      </div>
    </footer>
  );
}
