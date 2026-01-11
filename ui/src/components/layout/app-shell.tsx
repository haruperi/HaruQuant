"use client"

import * as React from "react"
import { Sidebar } from "@/components/layout/sidebar"
import { Navbar } from "@/components/layout/navbar"

export function AppShell({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = React.useState(true)

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-sans antialiased text-foreground">
      <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} />
      <div className="flex flex-col flex-1 w-0 overflow-hidden">
        <Navbar onMenuClick={() => setIsCollapsed(!isCollapsed)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-muted/20">
            {children}
        </main>
      </div>
    </div>
  )
}
