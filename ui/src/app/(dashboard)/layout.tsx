"use client"

import * as React from "react"
import { AppShell } from "@/components/layout/app-shell"
import { ProtectedRoute } from "@/components/auth/protected-route"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
       <AppShell>
          {children}
       </AppShell>
    </ProtectedRoute>
  )
}
