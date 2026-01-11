"use client"

import { usePathname } from "next/navigation"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Moon, Sun, Menu } from "lucide-react"
import { useTheme } from "next-themes"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import React from "react"

interface NavbarProps {
    onMenuClick?: () => void
}

export function Navbar({ onMenuClick }: NavbarProps) {
  const pathname = usePathname()
  const { setTheme } = useTheme()

  // Simple breadcrumb logic: /strategies/edit -> Home > Strategies > Edit
  const pathSegments = pathname.split('/').filter(Boolean)

  return (
    <div className="flex h-14 lg:h-[60px] items-center gap-4 border-b bg-background px-6 dark:bg-background">
      {/* Mobile Menu Trigger (Visible on Mobile Only if Sidebar is not present, but Sidebar handles mobile sheet)
          Actually, we might want a collapse trigger for Desktop here if we want to toggle sidebar size.
      */}
      {onMenuClick && (
          <Button variant="ghost" size="icon" onClick={onMenuClick} className="hidden md:flex mr-2">
              <Menu className="h-5 w-5"/>
          </Button>
      )}

      <div className="flex-1">
        <Breadcrumb className="hidden md:flex">
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink href="/">Home</BreadcrumbLink>
            </BreadcrumbItem>
            {pathSegments.length > 0 && <BreadcrumbSeparator />}
            {pathSegments.map((segment, index) => {
                const href = `/${pathSegments.slice(0, index + 1).join('/')}`
                const isLast = index === pathSegments.length - 1
                const title = segment.charAt(0).toUpperCase() + segment.slice(1)

                return (
                    <React.Fragment key={href}>
                        <BreadcrumbItem>
                            {isLast ? (
                                <BreadcrumbPage>{title}</BreadcrumbPage>
                            ) : (
                                <BreadcrumbLink href={href}>{title}</BreadcrumbLink>
                            )}
                        </BreadcrumbItem>
                        {!isLast && <BreadcrumbSeparator />}
                    </React.Fragment>
                )
            })}
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon">
              <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              <span className="sr-only">Toggle theme</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme("light")}>
              Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("dark")}>
              Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("system")}>
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
