"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const navItems = [
  { label: "Data", href: "/edge-lab" },
  { label: "Discovery", href: "/edge-lab/discovery" },
  { label: "Core Metric", href: "/edge-lab/core-metric" },
  { label: "Seasonality", href: "/edge-lab/seasonality" },
  { label: "SQX Import", href: "/edge-lab/sqx-import" },
  { label: "Monte Carlo Lab", href: "/edge-lab/monte-carlo-lab" },
]

export function EdgeLabNav() {
  const pathname = usePathname()

  return (
    <nav className="flex items-center gap-1 px-6 pb-4 overflow-x-auto">
      {navItems.map((item) => {
        const isActive =
          item.href === "/edge-lab"
            ? pathname === "/edge-lab"
            : pathname.startsWith(item.href)
        return (
          <Link key={item.href} href={item.href}>
            <Button
              variant={isActive ? "secondary" : "ghost"}
              size="sm"
              className={cn(
                "h-9 px-4 font-medium",
                isActive && "bg-primary/10 text-primary"
              )}
            >
              {item.label}
            </Button>
          </Link>
        )
      })}
    </nav>
  )
}
