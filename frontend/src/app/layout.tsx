import type { Metadata } from "next";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/space-grotesk";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";

export const metadata: Metadata = {
  title: "Vizora — Traffic Violation Detection",
  description: "Automated photo identification and classification of traffic violations using computer vision. Process surveillance images, detect 7 violation types, read plates, generate court-ready evidence.",
  icons: {
    icon: "/vizora-icon-generated.png",
    shortcut: "/vizora-icon-generated.png",
    apple: "/vizora-icon-generated.png",
  },
  openGraph: {
    title: "Vizora — Traffic Violation Detection",
    description: "AI-powered traffic violation detection from surveillance imagery",
    type: "website",
    siteName: "Vizora",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="dark h-full antialiased"
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <AuthProvider>
          <DashboardShell>{children}</DashboardShell>
        </AuthProvider>
      </body>
    </html>
  );
}
