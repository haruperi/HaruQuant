"use client"

import { useEffect, useState } from "react"
import { WifiOff } from "lucide-react"

export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false)

  useEffect(() => {
    function onOffline() {
      setIsOffline(true)
    }

    function onOnline() {
      setIsOffline(false)
    }

    window.addEventListener("offline", onOffline)
    window.addEventListener("online", onOnline)
      // Initial check (hydration mismatch safety: only render after mount if checking navigator)
      // But navigator.onLine is usually reliable in browsers. We'll stick to events for visual cleanliness.
      setIsOffline(!navigator.onLine)

    return () => {
      window.removeEventListener("offline", onOffline)
      window.removeEventListener("online", onOnline)
    }
  }, [])

  if (!isOffline) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex items-center gap-2 rounded-md bg-destructive text-destructive-foreground px-4 py-2 text-sm font-medium shadow-lg animate-in slide-in-from-bottom-2">
      <WifiOff className="h-4 w-4" />
      <span>You are currently offline</span>
    </div>
  )
}
