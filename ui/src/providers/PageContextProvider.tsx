"use client"

import * as React from "react"
import { usePathname } from "next/navigation"

import type { AiChatPageContextPayload } from "@/lib/ai-chat/contracts"
import { useAuth } from "@/lib/auth-context"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

interface PageContextValue {
  pageContext: AiChatPageContextPayload | null
  isLoading: boolean
  error: string | null
}

const PageContextContext = React.createContext<PageContextValue | null>(null)

export function PageContextProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { authenticatedFetch, isAuthenticated, isLoading: authLoading } = useAuth()
  const [pageContext, setPageContext] = React.useState<AiChatPageContextPayload | null>(null)
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (authLoading || !isAuthenticated) {
      return
    }

    let isMounted = true

    async function loadContext() {
      setIsLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({ route: pathname || "/" })
        const response = await authenticatedFetch(`${API_URL}/api/ai-chat/context?${params.toString()}`)
        if (!response.ok) {
          throw new Error("Failed to load page context")
        }
        const packet = (await response.json()) as { payload: AiChatPageContextPayload }
        if (isMounted) {
          setPageContext(packet.payload)
        }
      } catch (loadError) {
        console.error("Failed to load page context:", loadError)
        if (isMounted) {
          setError("Unable to load page context.")
          setPageContext(null)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void loadContext()

    return () => {
      isMounted = false
    }
  }, [authLoading, authenticatedFetch, isAuthenticated, pathname])

  const value = React.useMemo<PageContextValue>(
    () => ({
      pageContext,
      isLoading,
      error,
    }),
    [error, isLoading, pageContext],
  )

  return (
    <PageContextContext.Provider value={value}>
      {children}
    </PageContextContext.Provider>
  )
}

export function usePageContextValue() {
  const context = React.useContext(PageContextContext)
  if (!context) {
    throw new Error("usePageContextValue must be used within PageContextProvider")
  }
  return context
}
