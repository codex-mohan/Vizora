"use client";

import {
  Camera,
  ChevronsLeft,
  ChevronsRight,
  ClipboardCheck,
  FileSearch2,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  Settings2,
  Upload,
} from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import type React from "react";

import { VizoraIcon } from "@/components/brand/vizora-icon";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

const dashboardRoutes = ["/dashboard", "/process", "/analytics", "/violations", "/review-queue", "/cameras", "/evidence", "/settings"];

const primaryNav = [
  { href: "/dashboard", label: "Overview", description: "KPIs and live signal", icon: LayoutDashboard },
  { href: "/process", label: "Process", description: "Upload evidence", icon: Upload },
  { href: "/violations", label: "Violations", description: "Search records", icon: ClipboardCheck },
  { href: "/cameras", label: "Cameras", description: "Preprocessing modes", icon: Camera },
];

const secondaryNav = [
  { href: "/review-queue", label: "Review Queue", description: "Low confidence cases", icon: FileSearch2 },
];

const routeTitles: Record<string, { title: string; eyebrow: string }> = {
  "/dashboard": { title: "Overview", eyebrow: "Command center" },
  "/analytics": { title: "Overview", eyebrow: "Command center" },
  "/process": { title: "Process Evidence", eyebrow: "Upload and inference" },
  "/violations": { title: "Violations", eyebrow: "Evidence records" },
  "/review-queue": { title: "Review Queue", eyebrow: "Human review" },
  "/cameras": { title: "Cameras", eyebrow: "Preprocessing state" },
  "/settings": { title: "Settings", eyebrow: "Organization config" },
  "/evidence": { title: "Evidence Viewer", eyebrow: "Packet review" },
};

function isDashboardRoute(pathname: string) {
  return dashboardRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

function getRouteMeta(pathname: string) {
  if (pathname.startsWith("/evidence")) return routeTitles["/evidence"];
  return routeTitles[pathname] ?? routeTitles["/analytics"];
}

function NavLink({
  href,
  label,
  description,
  icon: Icon,
  collapsed = false,
  onNavigate,
}: {
  href: string;
  label: string;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const baseHref = href.split("?")[0].split("#")[0];
  const active = pathname === baseHref || pathname.startsWith(`${baseHref}/`);

  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-label={collapsed ? label : undefined}
      title={collapsed ? label : undefined}
      className={cn(
        "group relative flex items-center rounded-lg text-sm transition-all duration-300",
        collapsed ? "justify-center px-2 py-2.5" : "gap-3 px-3 py-2.5 hover:translate-x-0.5",
        active ? "bg-white/[0.08] text-white shadow-sm" : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-100",
      )}
    >
      {active && (
        <motion.span
          layoutId="dashboard-active-nav"
          className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-violet-300"
          transition={{ type: "spring", stiffness: 420, damping: 34 }}
        />
      )}
      <span
        className={cn(
          "grid size-8 place-items-center rounded-md border transition-all duration-300 group-hover:scale-105",
          active
            ? "border-violet-300/30 bg-violet-300/15 text-violet-200"
            : "border-white/[0.06] bg-white/[0.03] text-slate-500 group-hover:text-slate-200",
        )}
      >
        <Icon className="size-4" />
      </span>

      {!collapsed && (
        <span className="min-w-0">
          <span className="block font-medium">{label}</span>
          {description && <span className="block truncate text-xs text-slate-500">{description}</span>}
        </span>
      )}

      {collapsed && (
        <span className="pointer-events-none absolute left-[calc(100%+0.75rem)] top-1/2 z-50 -translate-y-1/2 rounded-lg border border-white/[0.08] bg-[#151823] px-3 py-2 opacity-0 shadow-xl shadow-black/30 transition-all duration-200 group-hover:translate-x-1 group-hover:opacity-100">
          <span className="block whitespace-nowrap text-sm font-medium text-white">{label}</span>
          {description && <span className="mt-0.5 block whitespace-nowrap text-xs text-slate-500">{description}</span>}
        </span>
      )}
    </Link>
  );
}

function Sidebar({
  collapsed = false,
  collapsible = false,
  onCollapseChange,
  onNavigate,
}: {
  collapsed?: boolean;
  collapsible?: boolean;
  onCollapseChange?: (collapsed: boolean) => void;
  onNavigate?: () => void;
}) {
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-full flex-col overflow-visible border-r border-white/[0.08] bg-[#0f1118]/95">
      <div className={cn("relative flex h-16 items-center border-b border-white/[0.08] px-3", collapsed ? "justify-center" : "justify-between gap-3")}>
        <Link href="/dashboard" onClick={onNavigate} className={cn("flex min-w-0 items-center gap-3", collapsed && "justify-center")} aria-label="Vizora dashboard">
          <VizoraIcon className="size-9 rounded-lg shadow-lg shadow-violet-300/15" />
          {!collapsed && (
            <div className="min-w-0">
              <p className="font-heading text-lg font-semibold leading-none text-white">Vizora</p>
              <p className="mt-1 font-metadata text-[10px] uppercase tracking-[0.2em] text-slate-500">Traffic Ops</p>
            </div>
          )}
        </Link>

        {collapsible && onCollapseChange && (
          <button
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => onCollapseChange(!collapsed)}
            className={cn(
              "hidden size-8 place-items-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-slate-400 transition-all duration-300 hover:border-violet-300/25 hover:bg-white/[0.06] hover:text-white lg:grid",
              collapsed && "absolute -right-4 bg-[#151823]",
            )}
          >
            {collapsed ? <ChevronsRight className="size-3.5" /> : <ChevronsLeft className="size-3.5" />}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-visible px-3 py-4">
        <div className="space-y-1">
          {primaryNav.map((item) => (
            <NavLink key={item.href} {...item} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
        </div>

        <div className="mt-6">
          {collapsed ? (
            <div className="mx-auto h-px w-8 bg-white/[0.08]" />
          ) : (
            <p className="px-3 font-metadata text-[10px] uppercase tracking-[0.24em] text-slate-600">Workflows</p>
          )}
          <div className="mt-2 space-y-1">
            {secondaryNav.map((item) => (
              <NavLink key={item.href} {...item} collapsed={collapsed} onNavigate={onNavigate} />
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-2 border-t border-white/[0.08] p-3">
        <NavLink
          href="/settings"
          label="Settings"
          description="Org config & sources"
          icon={Settings2}
          collapsed={collapsed}
          onNavigate={onNavigate}
        />
        <div className={cn("rounded-lg border border-white/[0.08] bg-white/[0.03] p-3 transition-all duration-300 hover:border-violet-300/20 hover:bg-white/[0.05]", collapsed && "flex justify-center p-2")}>
          {collapsed ? (
            <button
              aria-label={user ? "Sign out" : "Demo workspace"}
              title={user ? "Sign out" : "Demo workspace"}
              onClick={user ? logout : undefined}
              className="grid size-9 place-items-center rounded-md text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white"
            >
              <LogOut className="size-4" />
            </button>
          ) : (
            <>
              <p className="truncate text-sm font-medium text-white">{user?.org_name ?? "Demo workspace"}</p>
              <p className="mt-1 truncate text-xs text-slate-500">{user?.email ?? "Sign in to sync records"}</p>
              {user && (
                <Button variant="ghost" size="sm" onClick={logout} className="mt-3 w-full justify-start text-slate-400 hover:text-white">
                  <LogOut className="size-3.5" />
                  Sign out
                </Button>
              )}
            </>
          )}
        </div>
      </div>
    </aside>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const meta = useMemo(() => getRouteMeta(pathname), [pathname]);

  if (!isDashboardRoute(pathname)) return <>{children}</>;

  return (
    <div data-dashboard-shell className="min-h-screen bg-[#101219] text-slate-100">
      <div className={cn("fixed inset-y-0 left-0 z-40 hidden transition-[width] duration-300 ease-out lg:block", collapsed ? "w-20" : "w-64")}>
        <Sidebar collapsed={collapsed} collapsible onCollapseChange={setCollapsed} />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button aria-label="Close navigation" className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-[min(20rem,85vw)] shadow-2xl shadow-black/40">
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div className={cn("transition-[padding] duration-300 ease-out", collapsed ? "lg:pl-20" : "lg:pl-64")}>
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/[0.08] bg-[#101219]/88 px-4 backdrop-blur-xl sm:px-6">
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px overflow-hidden">
            <div className="h-full animate-glow-line bg-gradient-to-r from-transparent via-violet-300/50 to-transparent" />
          </div>
          <div className="flex min-w-0 items-center gap-3">
            <button
              aria-label="Open navigation"
              className="grid size-9 place-items-center rounded-lg border border-white/[0.08] bg-white/[0.04] text-slate-300 transition-all duration-300 hover:border-violet-300/25 hover:bg-white/[0.07] lg:hidden"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="size-4" />
            </button>
            <div className="min-w-0">
              <p className="font-metadata text-[10px] uppercase tracking-[0.24em] text-slate-500">{meta.eyebrow}</p>
              <h1 className="truncate font-heading text-xl font-semibold tracking-tight text-white">{meta.title}</h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden h-9 min-w-56 items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 text-sm text-slate-500 transition-colors duration-300 hover:border-violet-300/20 hover:text-slate-300 md:flex">
              <Search className="size-3.5" />
              Search evidence, plates, cameras
            </div>
            <Link href="/process" className="group inline-flex h-9 items-center rounded-lg bg-violet-300 px-3 text-sm font-medium text-slate-950 shadow-lg shadow-violet-300/10 transition-all duration-300 hover:-translate-y-0.5 hover:bg-violet-200 hover:shadow-violet-300/20">
              <Upload className="mr-1.5 size-3.5 transition-transform duration-300 group-hover:-translate-y-0.5" />
              New Evidence
            </Link>
          </div>
        </header>

        <div className="min-h-[calc(100vh-4rem)] bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.08),transparent_26rem)]">
          <motion.main
            key={pathname}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
          >
            {children}
          </motion.main>
        </div>
      </div>
    </div>
  );
}
