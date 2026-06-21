"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import { Eye, EyeOff, Loader2, ShieldCheck } from "lucide-react";
import { VizoraIcon } from "@/components/brand/vizora-icon";
import { useAuth } from "@/lib/auth-context";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const { login, loading: authLoading } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#101219]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="size-8 rounded-full border-2 border-violet-300 border-t-transparent"
        />
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#101219] px-4">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/3 size-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-violet-300/[0.06] blur-[120px]" />
        <div className="absolute bottom-0 left-0 size-[400px] rounded-full bg-sky-300/[0.04] blur-[100px]" />
        <div className="absolute right-0 top-0 size-[300px] rounded-full bg-amber-300/[0.03] blur-[80px]" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mb-10 flex flex-col items-center gap-4"
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
            className="relative"
          >
            <VizoraIcon className="size-14 rounded-2xl shadow-lg shadow-violet-300/20" />
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3, delay: 0.4 }}
              className="absolute -bottom-1 -right-1 grid size-5 place-items-center rounded-full bg-lime-300 text-slate-950"
            >
              <ShieldCheck className="size-3" />
            </motion.div>
          </motion.div>

          <div className="text-center">
            <h1 className="font-heading text-2xl font-semibold tracking-[-0.03em] text-white">
              Sign in to Vizora
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Traffic violation detection platform
            </p>
          </div>
        </motion.div>

        <motion.form
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
          onSubmit={handleSubmit}
          className="space-y-5 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 shadow-2xl shadow-black/30 backdrop-blur-xl"
        >
          <motion.div
            initial={false}
            animate={error ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            {error && (
              <div className="rounded-xl border border-red-300/20 bg-red-300/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}
          </motion.div>

          <div className="space-y-1.5">
            <label htmlFor="email" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Email
            </label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="h-11 border-white/[0.06] bg-white/[0.03] text-slate-100 placeholder:text-slate-600"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Password
            </label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="h-11 border-white/[0.06] bg-white/[0.03] pr-10 text-slate-100 placeholder:text-slate-600"
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-300"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="h-12 w-full cursor-pointer bg-violet-400 text-[#100f18] shadow-lg shadow-violet-300/15 transition-all duration-300 hover:bg-violet-300 hover:shadow-violet-300/25"
          >
            {submitting ? (
              <Loader2 className="mr-2 size-4 animate-spin" />
            ) : (
              <ShieldCheck className="mr-2 size-4" />
            )}
            {submitting ? "Signing in\u2026" : "Sign in"}
          </Button>
        </motion.form>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="mt-6 text-center text-sm text-slate-500"
        >
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-medium text-violet-300 transition-colors hover:text-violet-200"
          >
            Create one
          </Link>
        </motion.p>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mt-8 text-center font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-700"
        >
          Flipkart Gridlock 2.0 &middot; Traffic Violation Detection
        </motion.p>
      </div>
    </div>
  );
}
