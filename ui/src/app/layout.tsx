import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider"
import { AppShell } from "@/components/layout/app-shell"
import { ErrorBoundary } from "@/components/error-boundary"
import { OfflineBanner } from "@/components/offline-banner"
import { AuthProvider } from "@/lib/auth-context"
import { Toaster } from "sonner"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HaruQuant",
  description: "Professional Algorithmic Trading System Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <ErrorBoundary>
            <ThemeProvider
                attribute="class"
                defaultTheme="system"
                enableSystem
                disableTransitionOnChange
            >
                <OfflineBanner />
                <AuthProvider>
                    {children}
                </AuthProvider>
                <Toaster richColors position="top-right" />
            </ThemeProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
