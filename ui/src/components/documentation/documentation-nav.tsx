"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronDown, Book, Code2, ShieldCheck, Bot, TrendingUp, BookOpen, FileText, Settings } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"

interface NavItem {
  label: string
  href: string
  icon?: any
}

interface NavSection {
  label: string
  href: string
  items: NavItem[]
  icon?: any
}

const documentationNavItems: NavSection[] = [
  {
    label: "Fundamentals",
    href: "/documentation/fundamentals",
    items: [
      { label: "Key Concepts", href: "/documentation/fundamentals/key-concepts", icon: FileText },
      { label: "Strategy Basic Components", href: "/documentation/fundamentals/strategy-basic-components", icon: FileText },
      { label: "Order Types", href: "/documentation/fundamentals/order-types", icon: FileText },
      { label: "Strategies to Trade", href: "/documentation/fundamentals/strategies-to-trade", icon: FileText },
      { label: "Financial Instruments", href: "/documentation/fundamentals/financial-instruments", icon: FileText },
      { label: "Perfect Market Selection", href: "/documentation/fundamentals/perfect-market-selection", icon: FileText },
      { label: "Things to Keep an Eye On", href: "/documentation/fundamentals/things-to-keep-an-eye-on", icon: FileText },
      { label: "Performance Metrics Analysis", href: "/documentation/fundamentals/performance-metrics-analysis", icon: FileText },
    ],
    icon: Book
  },
  {
    label: "Development",
    href: "/documentation/development",
    items: [
      {
        label: "Chart Setup",
        href: "/documentation/development/chart-setup",
        icon: FileText
      },
      {
        label: "Building Blocks",
        href: "/documentation/development/building-blocks",
        icon: FileText
      },
      {
        label: "Strategy Filters",
        href: "/documentation/development/strategy-filters",
        icon: FileText
      },
      {
        label: "Market Edge",
        href: "/documentation/development/market-edge",
        icon: FileText
      },
      {
        label: "Ranking",
        href: "/documentation/development/ranking",
        icon: FileText
      },
      {
        label: "Special SQX Strategies",
        href: "/documentation/development/special-sqx-strategies",
        icon: FileText
      },
      {
        label: "Stop Loss Analysis",
        href: "/documentation/development/stop-loss-analysis",
        icon: FileText
      },
      {
        label: "Backtesting Biases",
        href: "/documentation/development/backtesting-biases",
        icon: FileText
      }
    ],
    icon: Code2
  },
  {
    label: "Robustness",
    href: "/documentation/robustness",
    items: [],
    icon: ShieldCheck
  },
  {
    label: "Automation",
    href: "/documentation/automation",
    items: [],
    icon: Bot
  },
  {
    label: "Trading",
    href: "/documentation/trading",
    items: [],
    icon: TrendingUp
  },
  {
    label: "Admin",
    href: "/documentation/manage",
    items: [],
    icon: Settings
  }
]

export function DocumentationNav() {
  const pathname = usePathname()

  return (
    <nav className="flex items-center gap-1 px-6 pb-4 mt-4 overflow-x-auto">
      {documentationNavItems.map((section) => {
        const isActive = pathname.startsWith(section.href)
        const hasItems = section.items.length > 0

        // For now, since we don't have sub-pages yet, we treat them as simple links or dropdowns with no items (which acts like a button basically if we wanted, but let's stick to the pattern)
        // ideally if it has dropdown items we show them. The user said "All these tabs will have dropdowns of pages we will develop later".
        // So I will implement the structure but the arrays are empty.
        // If arrays are empty, the existing logic in performance-nav shows as a simple button.
        // I'll keep it consistent.

        if (!hasItems) {
            // Simple link behavior for now until items are added
           const Icon = section.icon || BookOpen
           return (
             <Link key={section.href} href={section.href}>
               <Button
                 variant={isActive ? "secondary" : "ghost"}
                 size="sm"
                 className={cn(
                   "h-9 px-4 font-medium",
                   isActive && "bg-primary/10 text-primary"
                 )}
               >
                  <span className="mr-2">
                    <Icon className="h-4 w-4" />
                  </span>
                 {section.label}
                 {/*  Show chevron to hint at dropdown capability even if empty? No, better stick to standard behavior */}
               </Button>
             </Link>
           )
        }

        return (
          <DropdownMenu key={section.href}>
            <DropdownMenuTrigger asChild>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                size="sm"
                className={cn(
                  "h-9 px-4 font-medium",
                  isActive && "bg-primary/10 text-primary"
                )}
              >
                {section.label}
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              className="w-56"
            >
              {section.items.map((item) => {
                const ItemIcon = item.icon
                const isItemActive = pathname === item.href

                return (
                  <DropdownMenuItem key={item.href} asChild>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2 cursor-pointer",
                        isItemActive && "bg-accent"
                      )}
                    >
                      {ItemIcon && <ItemIcon className="h-4 w-4 text-muted-foreground" />}
                      <span className="truncate">{item.label}</span>
                    </Link>
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        )
      })}
    </nav>
  )
}
