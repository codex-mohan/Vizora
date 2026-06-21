"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import { Eye, EyeOff, Loader2, Sparkles } from "lucide-react";
import { VizoraIcon } from "@/components/brand/vizora-icon";
import { useAuth } from "@/lib/auth-context";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const passwordStrength = (pw: string): { label: string; color: string; width: string } => {
  if (pw.length === 0) return { label: "", color: "bg-slate-700", width: "w-0" };
  if (pw.length < 6) return { label: "Weak", color: "bg-red-400", width: "w-1/4" };
  if (pw.length < 8) return { label: "Fair", color: "bg-amber-400", width: "w-2/4" };
  if (/[A-Z]/.test(pw) && /[0-9]/.test(pw) && /[^a-zA-Z0-9]/.test(pw))
    return { label: "Strong", color: "bg-lime-400", width: "w-full" };
  return { label: "Good", color: "bg-sky-400", width: "w-3/4" };
};

export default function SignupPage() {
  const { signup, loading: authLoading } = useAuth();
  const router = useRouter();

  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [slugManual, setSlugManual] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleOrgNameChange = useCallback(
    (value: string) => {
      setOrgName(value);
      if (!slugManual) {
        setOrgSlug(slugify(value));
      }
    },
    [slugManual],
  );

  const strength = passwordStrength(password);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    if (!orgSlug) {
      setError("Organization slug is required");
      return;
    }

    setSubmitting(true);
    try {
      await signup({
        org_name: orgName,
        org_slug: orgSlug,
        email,
        password,
        full_name: fullName,
      });
      router.push("/process");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#101219] px-4 py-12">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute right-1/4 top-1/4 size-[500px] rounded-full bg-violet-300/[0.06] blur-[120px]" />
        <div className="absolute bottom-1/4 left-1/4 size-[400px] rounded-full bg-sky-300/[0.05] blur-[100px]" />
        <div className="absolute bottom-0 right-0 size-[300px] rounded-full bg-lime-300/[0.03] blur-[80px]" />
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
              <Sparkles className="size-3" />
            </motion.div>
          </motion.div>

          <div className="text-center">
            <h1 className="font-heading text-2xl font-semibold tracking-[-0.03em] text-white">
              Create your account
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Set up your organization to start detecting violations
            </p>
          </div>
        </motion.div>

        <motion.form
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15, ease: "easeOut" }}
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 shadow-2xl shadow-black/30 backdrop-blur-xl"
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
            <label htmlFor="orgName" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Organization name
            </label>
            <Input
              id="orgName"
              type="text"
              placeholder="Mumbai Traffic Police"
              value={orgName}
              onChange={(e) => handleOrgNameChange(e.target.value)}
              required
              className="h-11 border-white/[0.06] bg-white/[0.03] text-slate-100 placeholder:text-slate-600"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="orgSlug" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Organization slug
            </label>
            <Input
              id="orgSlug"
              type="text"
              placeholder="mumbai-traffic-police"
              value={orgSlug}
              onChange={(e) => {
                setSlugManual(true);
                setOrgSlug(slugify(e.target.value));
              }}
              required
              className="h-11 border-white/[0.06] bg-white/[0.03] font-mono text-slate-100 placeholder:text-slate-600"
            />
            <p className="text-xs text-slate-600">
              Used in URLs. Auto-generated from name &mdash; edit if needed.
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="fullName" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Full name
            </label>
            <Input
              id="fullName"
              type="text"
              placeholder="Priya Sharma"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              autoComplete="name"
              className="h-11 border-white/[0.06] bg-white/[0.03] text-slate-100 placeholder:text-slate-600"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="email" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Email
            </label>
            <Input
              id="email"
              type="email"
              placeholder="priya@example.com"
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
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
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
            {password.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-1.5 pt-1"
              >
                <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    className={`h-full rounded-full transition-all duration-500 ${strength.color} ${strength.width}`}
                  />
                </div>
                <p className={`text-xs ${strength.label === "Strong" ? "text-lime-400" : strength.label === "Good" ? "text-sky-400" : strength.label === "Fair" ? "text-amber-400" : "text-red-400"}`}>
                  {strength.label}
                </p>
              </motion.div>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="confirmPassword" className="font-metadata text-xs uppercase tracking-[0.2em] text-slate-400">
              Confirm password
            </label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirm ? "text" : "password"}
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="h-11 border-white/[0.06] bg-white/[0.03] pr-10 text-slate-100 placeholder:text-slate-600"
              />
              <button
                type="button"
                tabIndex={-1}
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-300"
                aria-label={showConfirm ? "Hide password" : "Show password"}
              >
                {showConfirm ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            {confirmPassword.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="pt-0.5"
              >
                {password === confirmPassword ? (
                  <p className="text-xs text-lime-400">Passwords match</p>
                ) : (
                  <p className="text-xs text-red-400">Passwords do not match</p>
                )}
              </motion.div>
            )}
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="h-12 w-full cursor-pointer bg-violet-400 text-[#100f18] shadow-lg shadow-violet-300/15 transition-all duration-300 hover:bg-violet-300 hover:shadow-violet-300/25"
          >
            {submitting ? (
              <Loader2 className="mr-2 size-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 size-4" />
            )}
            {submitting ? "Creating account\u2026" : "Create account"}
          </Button>
        </motion.form>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="mt-6 text-center text-sm text-slate-500"
        >
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-violet-300 transition-colors hover:text-violet-200"
          >
            Sign in
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
