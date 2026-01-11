"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { Moon, Sun, Monitor, Loader2 } from "lucide-react"
import { useSettings } from "@/lib/use-settings"

export function GeneralSettings() {
  const { setTheme, theme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const { settings, isLoading, updateSettings } = useSettings()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    // Sync theme from settings
    if (settings && mounted) {
      setTheme(settings.theme)
    }
  }, [settings, mounted, setTheme])

  const handleThemeChange = async (newTheme: string) => {
    setTheme(newTheme)
    await updateSettings({ theme: newTheme })
  }

  const handleTimezoneChange = async (newTimezone: string) => {
    await updateSettings({ timezone: newTimezone })
  }

  const handleLogVerbosityChange = async (newVerbosity: string) => {
    await updateSettings({ log_verbosity: newVerbosity })
  }

  const handlePerformanceModeChange = async (enabled: boolean) => {
    await updateSettings({ performance_mode: enabled ? "performance" : "balanced" })
  }

  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>
            Customize the look and feel of the application.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
             <div className="space-y-1">
                <Label>Theme Preference</Label>
                <p className="text-xs text-muted-foreground">Select your preferred color scheme.</p>
             </div>
             <div className="flex bg-muted p-1 rounded-lg gap-1">
                <Button
                    variant={theme === 'light' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => handleThemeChange('light')}
                    className="h-8 w-20"
                >
                    <Sun className="mr-2 h-4 w-4" /> Light
                </Button>
                <Button
                    variant={theme === 'dark' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => handleThemeChange('dark')}
                    className="h-8 w-20"
                >
                    <Moon className="mr-2 h-4 w-4" /> Dark
                </Button>
                <Button
                    variant={theme === 'system' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => handleThemeChange('system')}
                    className="h-8 w-20"
                >
                    <Monitor className="mr-2 h-4 w-4" /> System
                </Button>
             </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Localization & Time</CardTitle>
          <CardDescription>
            Configure how time and dates are displayed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
           <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <Label>Timezone</Label>
                    <p className="text-xs text-muted-foreground">Your dashboard will use this timezone.</p>
                </div>
                <Select
                  value={settings?.timezone || "UTC"}
                  onValueChange={handleTimezoneChange}
                >
                    <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select timezone" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="local">Local System Time</SelectItem>
                        <SelectItem value="UTC">UTC (Coordinated Universal Time)</SelectItem>
                        <SelectItem value="EST">EST (New York)</SelectItem>
                        <SelectItem value="GMT">GMT (London)</SelectItem>
                        <SelectItem value="JST">JST (Tokyo)</SelectItem>
                    </SelectContent>
                </Select>
           </div>
        </CardContent>
      </Card>

       <Card>
        <CardHeader>
          <CardTitle>System & Logging</CardTitle>
          <CardDescription>
            Manage application logging and performance.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
           <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <Label>Log Verbosity</Label>
                    <p className="text-xs text-muted-foreground">Controls the detail level of logs stored.</p>
                </div>
                <Select
                  value={settings?.log_verbosity || "info"}
                  onValueChange={handleLogVerbosityChange}
                >
                    <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select level" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="debug">Debug (All events)</SelectItem>
                        <SelectItem value="info">Info (Standard)</SelectItem>
                        <SelectItem value="warn">Warning & Error only</SelectItem>
                        <SelectItem value="error">Error only</SelectItem>
                    </SelectContent>
                </Select>
           </div>

           <div className="flex items-center justify-between pt-2">
                <div className="space-y-0.5">
                    <Label>Performance Mode</Label>
                    <p className="text-xs text-muted-foreground">Reduce animations for lower CPU usage.</p>
                </div>
                <Switch
                  checked={settings?.performance_mode === "performance"}
                  onCheckedChange={handlePerformanceModeChange}
                />
           </div>
        </CardContent>
      </Card>
    </div>
  )
}
