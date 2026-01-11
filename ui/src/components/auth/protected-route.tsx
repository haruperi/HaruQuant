"use client"

import { useAuth } from "@/lib/auth-context"
import { useRouter, usePathname } from "next/navigation"
import * as React from "react"
import { Loader2 } from "lucide-react"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
  const [verifying, setVerifying] = React.useState(true)

  React.useEffect(() => {
    const verifyToken = async () => {
      // If not authenticated, no need to verify
      if (!isAuthenticated) {
        setVerifying(false)
        return
      }

      // Verify token is still valid on backend
      const token = localStorage.getItem("hq_auth_token")
      if (!token) {
        logout()
        setVerifying(false)
        return
      }

      try {
        // Make a lightweight API call to verify token
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/strategies/`, {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        })

        if (response.status === 401) {
          // Token is invalid or expired
          logout()
        }
      } catch (error) {
        // Network error, allow access but token will be verified on next API call
        console.error("Failed to verify token:", error)
      } finally {
        setVerifying(false)
      }
    }

    if (!isLoading) {
      verifyToken()
    }
  }, [isLoading, isAuthenticated, logout])

  React.useEffect(() => {
    if (!isLoading && !verifying && !isAuthenticated) {
      router.push("/login")
    }
  }, [isLoading, verifying, isAuthenticated, router])

  if (isLoading || verifying) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // If not authenticated, we render nothing while redirect happens
  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}
