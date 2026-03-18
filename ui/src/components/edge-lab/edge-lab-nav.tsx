"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useEdgeLabData } from "@/contexts/edge-lab-data-context"

const navItems = [
  { label: "Data", href: "/edge-lab", prerequisite: "always" },
  { label: "Core Metric", href: "/edge-lab/core-metric", prerequisite: "dataset" },
  { label: "Seasonality", href: "/edge-lab/seasonality", prerequisite: "core_metric" },
  { label: "Market Structure", href: "/edge-lab/market-structure", prerequisite: "seasonality" },
  { label: "Scorecard", href: "/edge-lab/scorecard", prerequisite: "market_structure" },
  { label: "Automation", href: "/edge-lab/automation", prerequisite: "always" },
  { label: "Discovery", href: "/edge-lab/discovery", prerequisite: "dataset" },
  { label: "SQX Import", href: "/edge-lab/sqx-import" },
  { label: "Monte Carlo Lab", href: "/edge-lab/monte-carlo-lab" },
]

export function EdgeLabNav() {
  const pathname = usePathname()
  const { dataset, coreMetricProfile, seasonalityResult, marketStructureProfile } = useEdgeLabData()

  const isEnabled = (prerequisite?: string) => {
    if (!prerequisite || prerequisite === "always") return true
    if (prerequisite === "dataset") return Boolean(dataset)
    if (prerequisite === "core_metric") return Boolean(coreMetricProfile)
    if (prerequisite === "seasonality") return Boolean(seasonalityResult)
    if (prerequisite === "market_structure") return Boolean(marketStructureProfile)
    return true
  }

  return (
    <nav className="flex items-center gap-1 px-6 pb-4 overflow-x-auto">
      {navItems.map((item) => {
        const isActive =
          item.href === "/edge-lab"
            ? pathname === "/edge-lab"
            : pathname.startsWith(item.href)
        const enabled = isEnabled(item.prerequisite)
        const button = (
          <Button
            variant={isActive ? "secondary" : "ghost"}
            size="sm"
            disabled={!enabled}
            className={cn(
              "h-9 px-4 font-medium",
              isActive && "bg-primary/10 text-primary"
            )}
          >
            {item.label}
          </Button>
        )
        return (
          enabled ? (
            <Link key={item.href} href={item.href}>
              {button}
            </Link>
          ) : (
            <div key={item.href}>{button}</div>
          )
        )
      })}
    </nav>
  )
}
