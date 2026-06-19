import type { Metadata } from "next";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/space-grotesk";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vizora — Traffic Violation Detection",
  description: "Automated photo identification and classification of traffic violations using computer vision. Process surveillance images, detect 7 violation types, read plates, generate court-ready evidence.",
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
      <body className="min-h-full flex flex-col bg-background text-foreground">{children}</body>
    </html>
  );
}
