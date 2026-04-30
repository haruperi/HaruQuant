"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  LayoutDashboard,
  Database,
  BrainCircuit,
  Activity,
  ShieldCheck,
  BarChart,
  Settings,
  Menu,
  X,
  FlaskConical,
  LogOut,
  User,
  ChevronDown,
  ChevronRight,
  Table,
  LineChart as LineChartIcon,
  BookOpen,
  Upload,
  Play,
  TrendingUp,
} from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useState, useEffect } from "react"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
    isCollapsed?: boolean
    setIsCollapsed?: (collapsed: boolean) => void
}

const routes = [
    {
      label: "Dashboard",
      icon: LayoutDashboard,
      href: "/",
      color: "text-sky-500",
    },
    {
      label: "Chart",
      icon: LineChartIcon,
      href: "/chart",
      color: "text-violet-500",
      subRoutes: [
        {
          label: "Quotes",
          href: "/chart/quotes",
        },
        {
          label: "Forex Calendar",
          href: "/chart/forex-calendar",
        },
      ],
    },
    {
      label: "Strategies",
      icon: BrainCircuit,
      href: "/strategies",
      color: "text-pink-700",
    },
    {
      label: "Simulation",
      icon: Play,
      href: "/simulation",
      color: "text-green-600",
    },
    {
      label: "Optimization",
      icon: FlaskConical,
      href: "/optimization",
      color: "text-amber-500",
    },
    {
      label: "Edge Lab",
      icon: Table,
      href: "/edge-lab",
      color: "text-teal-500",
    },
    {
      label: "Performance Report",
      icon: BarChart,
      href: "/performance",
      color: "text-indigo-500",
    },
    {
      label: "Live Trading",
      icon: Activity,
      href: "/live",
      color: "text-emerald-500",
    },
    {
      label: "Operator",
      icon: ShieldCheck,
      href: "/operator",
      color: "text-orange-400",
    },
    {
      label: "Tools",
      icon: TrendingUp,
      href: "/tools",
      color: "text-cyan-500",
    },
    {
      label: "Documentation",
      icon: BookOpen,
      href: "/documentation",
      color: "text-blue-500",
    },
    {
      label: "Settings",
      icon: Settings,
      href: "/settings",
      color: "text-gray-500",
    },
]

interface SidebarItemProps {
    route: any
    pathname: string
    isCollapsed: boolean
    openSubmenus: Record<string, boolean>
    toggleSubmenu: (label: string) => void
    level: number
    onMobileClose?: () => void
}

function SidebarItem({ route, pathname, isCollapsed, openSubmenus, toggleSubmenu, level, onMobileClose }: SidebarItemProps) {
    const isActive = pathname === route.href || (route.subRoutes && pathname.startsWith(route.href))
    const isOpen = !!openSubmenus[route.label]
    const hasSubRoutes = Array.isArray(route.subRoutes) && route.subRoutes.length > 0

    return (
        <div className="mb-1 w-full">
            <div className={cn("relative flex items-center w-full", isCollapsed ? "justify-center" : "")}>
                <div className={cn("flex-1 min-w-0", !isCollapsed && hasSubRoutes ? "pr-8" : "")}>
                    <Button
                        asChild
                        variant={isActive ? "secondary" : "ghost"}
                        className={cn(
                            "w-full justify-start text-zinc-400 hover:text-white hover:bg-white/10 h-auto py-2",
                            isActive && "bg-white/10 text-white",
                            isCollapsed && "justify-center px-0"
                        )}
                        style={{ paddingLeft: !isCollapsed ? `${level * 12 + 16}px` : undefined }}
                    >
                        <Link
                            href={route.href}
                            onClick={() => {
                                if (!route.subRoutes && onMobileClose) onMobileClose()
                            }}
                        >
                            {route.icon && <route.icon className={cn(level === 0 ? "h-5 w-5" : "h-4 w-4", route.color, isCollapsed ? "mr-0" : "mr-3")} />}
                            {!isCollapsed && <span className={cn("flex-1 text-left truncate", level > 0 && "text-xs")}>{route.label}</span>}
                        </Link>
                    </Button>
                </div>
                {!isCollapsed && hasSubRoutes && (
                    <button
                        type="button"
                        onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            toggleSubmenu(route.label)
                        }}
                        className="absolute right-0 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white p-2 transition-colors flex items-center justify-center z-10"
                        title={isOpen ? "Collapse" : "Expand"}
                        aria-label={isOpen ? `Collapse ${route.label}` : `Expand ${route.label}`}
                    >
                        {isOpen ? (
                            <ChevronDown className="h-4 w-4" />
                        ) : (
                            <ChevronRight className="h-4 w-4" />
                        )}
                    </button>
                )}
            </div>
            {!isCollapsed && hasSubRoutes && isOpen && (
                <div className="space-y-1 mt-1">
                    {route.subRoutes.map((subRoute: any) => (
                        <SidebarItem
                            key={subRoute.href}
                            route={subRoute}
                            pathname={pathname}
                            isCollapsed={isCollapsed}
                            openSubmenus={openSubmenus}
                            toggleSubmenu={toggleSubmenu}
                            level={level + 1}
                            onMobileClose={onMobileClose}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}

export function Sidebar({ className, isCollapsed, setIsCollapsed }: SidebarProps) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const { user, logout } = useAuth()
  const [openSubmenus, setOpenSubmenus] = useState<Record<string, boolean>>({})

  const toggleSubmenu = (label: string) => {
    setOpenSubmenus(prev => ({ ...prev, [label]: !prev[label] }))
  }

  // Effect to automatically open parents when navigating
  useEffect(() => {
    const findAndOpenParents = (items: any[]) => {
        items.forEach(item => {
            if (item.subRoutes) {
                // Check if any subroute (recursive) matches the current pathname
                const hasActiveSub = (routes: any[]): boolean => {
                    return routes.some(r =>
                        pathname === r.href || (r.subRoutes && hasActiveSub(r.subRoutes))
                    )
                }

                if (hasActiveSub(item.subRoutes)) {
                    setOpenSubmenus(prev => ({ ...prev, [item.label]: true }))
                    findAndOpenParents(item.subRoutes)
                }
            }
        })
    }
    findAndOpenParents(routes)
  }, [pathname])

  const effectiveIsCollapsed = !!(isCollapsed && !isHovered)

  return (
    <>
        {/* Mobile Sidebar */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
             <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden fixed top-4 left-4 z-50">
                    <Menu />
                </Button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-72">
                <div className="space-y-4 py-4 flex flex-col h-full bg-slate-900 text-white">
                    <div className="px-3 py-2 flex-1">
                        <Link href="/" className="flex items-center pl-3 mb-14">
                            <h1 className="text-2xl font-bold">HaruQuant</h1>
                        </Link>
                        <div className="space-y-1">
                            {routes.map((route) => (
                                <SidebarItem
                                    key={route.href}
                                    route={route}
                                    pathname={pathname}
                                    isCollapsed={false}
                                    openSubmenus={openSubmenus}
                                    toggleSubmenu={toggleSubmenu}
                                    level={0}
                                    onMobileClose={() => setMobileOpen(false)}
                                />
                            ))}
                        </div>
                        </div>
                    {/* Mobile Footer */}
                     <div className="px-3 py-4 border-t border-white/10">
                        {user && (
                            <div className="flex items-center gap-x-3 mb-3 px-3">
                                <div className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center">
                                    <User className="h-4 w-4 text-white" />
                                </div>
                                <div className="flex flex-col">
                                    <p className="text-sm font-medium text-white">
                                        {user.full_name || user.username}
                                    </p>
                                    <p className="text-xs text-zinc-400 truncate w-32">{user.email}</p>
                                </div>
                            </div>
                        )}
                        <Button
                            onClick={logout}
                            variant="ghost"
                            className="w-full justify-start text-zinc-400 hover:text-white hover:bg-white/10"
                        >
                            <LogOut className="h-5 w-5 mr-3" />
                            Logout
                        </Button>
                    </div>
                </div>
            </SheetContent>
        </Sheet>

        {/* Desktop Sidebar */}
      <div
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          "relative hidden md:flex h-full flex-col border-r bg-slate-900 text-white transition-all duration-300 z-20",
          effectiveIsCollapsed ? "w-[80px]" : "w-72",
          className
        )}
      >
        <div className="flex h-14 items-center border-b border-white/10 px-4 lg:h-[60px] justify-between">
            {!effectiveIsCollapsed && (
             <Link className="flex items-center gap-2 font-semibold" href="/">
                <span className="">HaruQuant</span>
             </Link>
            )}
            {effectiveIsCollapsed && (
                 <Link className="flex items-center justify-center w-full" href="/">
                    <span className="font-bold">HQ</span>
                 </Link>
             )}
        </div>

        <ScrollArea className="flex-1 py-4">
            <nav className="grid gap-1 px-2 group-[[data-collapsed=true]]:justify-center group-[[data-collapsed=true]]:px-2">
                {routes.map((route) => (
                    <SidebarItem
                      key={route.href}
                      route={route}
                      pathname={pathname}
                      isCollapsed={effectiveIsCollapsed}
                      openSubmenus={openSubmenus}
                      toggleSubmenu={toggleSubmenu}
                      level={0}
                    />
                ))}
            </nav>
        </ScrollArea>


        {/* Desktop Footer */}
        {user && (
            <div className="border-t border-white/10 p-3">
                 <div className={cn(
                     "flex items-center gap-x-3 px-2",
                     effectiveIsCollapsed ? "justify-center" : "justify-between"
                 )}>
                     <div className="flex items-center gap-x-3 overflow-hidden">
                         <div className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                            <User className="h-4 w-4 text-white" />
                        </div>
                        {!effectiveIsCollapsed && (
                            <div className="flex flex-col overflow-hidden">
                                <p className="text-sm font-medium text-white truncate w-32">
                                    {user.full_name || user.username}
                                </p>
                                <p className="text-xs text-zinc-400 truncate w-32">{user.email}</p>
                            </div>
                        )}
                    </div>
                     {!effectiveIsCollapsed && (
                         <Button
                            onClick={logout}
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-white/10"
                        >
                            <LogOut className="h-4 w-4" />
                        </Button>
                     )}
                </div>
            </div>
        )}
      </div>
    </>
  )
}
