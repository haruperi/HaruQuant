"use client"

import * as React from "react"
import { usePathname } from "next/navigation"

import type {
  AiChatDomSnapshot,
  AiChatPageContextPayload,
  AiChatPageContextRegistration,
  AiChatDomTableSnapshot,
  AiChatSemanticBlock,
  AiChatPageIntelligence,
  AiChatDomActionableElementSnapshot,
} from "@/lib/ai-chat/contracts"
import { mergePageIntelligence, pageIntelligenceToSemanticBlocks } from "@/lib/ai-chat/page-intelligence"
import { useAuth } from "@/lib/auth-context"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
const DOM_TEXT_LIMIT = 2500
const DOM_HEADING_LIMIT = 8
const DOM_TABLE_LIMIT = 2
const DOM_TABLE_ROW_LIMIT = 8
const DOM_TABLE_COL_LIMIT = 6
const DOM_SEMANTIC_BLOCK_LIMIT = 24
const DOM_ACTIONABLE_ELEMENT_LIMIT = 80

type RegisteredStateMap = Record<string, AiChatPageContextRegistration>

interface PageContextValue {
  pageContext: AiChatPageContextPayload | null
  isLoading: boolean
  error: string | null
  registerPageContext: (id: string, registration: AiChatPageContextRegistration, callbacks?: Record<string, (params: Record<string, unknown>) => void | Promise<void>>) => void
  unregisterPageContext: (id: string) => void
  executeAction: (actionId: string, params: Record<string, unknown>) => Promise<boolean>
}

const PageContextContext = React.createContext<PageContextValue | null>(null)

function normalizeText(value: string | null | undefined) {
  return (value || "").replace(/\s+/g, " ").trim()
}

function isElementVisible(element: Element): boolean {
  if (!(element instanceof HTMLElement)) {
    return false
  }
  if (element.hidden || element.getAttribute("aria-hidden") === "true") {
    return false
  }
  const style = window.getComputedStyle(element)
  if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) {
    return false
  }
  const rect = element.getBoundingClientRect()
  return rect.width > 0 && rect.height > 0
}

function actionableLabel(element: HTMLElement): string {
  return normalizeText(
    element.getAttribute("aria-label")
    || element.getAttribute("title")
    || element.textContent
    || element.getAttribute("href")
    || "",
  )
}

function buildActionableElements(root: Element): AiChatDomActionableElementSnapshot[] {
  if (typeof window === "undefined") {
    return []
  }

  const candidates = Array.from(
    root.querySelectorAll<HTMLElement>(
      [
        "button",
        "a[href]",
        "[role='button']",
        "[role='menuitem']",
        "[role='tab']",
        "input[type='button']",
        "input[type='submit']",
      ].join(","),
    ),
  )
    .filter((element) => isElementVisible(element))
    .filter((element) => !element.hasAttribute("disabled") && element.getAttribute("aria-disabled") !== "true")
    .map((element, index) => {
      const selector = `ai-chat-actionable-${index}`
      element.setAttribute("data-ai-chat-actionable", selector)
      const tagName = element.tagName.toLowerCase()
      return {
        selector: `[data-ai-chat-actionable="${selector}"]`,
        label: actionableLabel(element),
        role: element.getAttribute("role") || (tagName === "a" ? "link" : tagName === "button" ? "button" : "control"),
        tagName,
        index,
      }
    })
    .filter((item) => item.label.length > 0)

  return candidates.slice(0, DOM_ACTIONABLE_ELEMENT_LIMIT)
}

function parseSemanticBlocks(root: Element, tables: AiChatDomTableSnapshot[], headings: string[], textExcerpt: string | null): AiChatSemanticBlock[] {
  const scriptedBlocks = Array.from(
    root.querySelectorAll("script[type='application/json'][data-ai-chat-semantic-block]"),
  )
    .slice(0, DOM_SEMANTIC_BLOCK_LIMIT)
    .flatMap((node, index) => {
      try {
        const parsed = JSON.parse(node.textContent || "") as AiChatSemanticBlock
        if (!parsed || typeof parsed !== "object" || typeof parsed.id !== "string" || typeof parsed.blockType !== "string") {
          return []
        }
        return [{
          ...parsed,
          id: parsed.id || `semantic_block_${index}`,
        }]
      } catch {
        return []
      }
    })

  const derivedBlocks: AiChatSemanticBlock[] = []

  if (headings.length > 0) {
    derivedBlocks.push({
      id: "dom:headings",
      blockType: "heading",
      title: "Visible headings",
      summary: headings.slice(0, 6).join(" | "),
      keywords: headings.slice(0, 8),
    })
  }

  if (textExcerpt) {
    derivedBlocks.push({
      id: "dom:text_excerpt",
      blockType: "text",
      title: "Visible text excerpt",
      summary: textExcerpt,
      keywords: textExcerpt.split(/\s+/).slice(0, 24),
    })
  }

  tables.slice(0, DOM_TABLE_LIMIT).forEach((table, index) => {
    derivedBlocks.push({
      id: `dom:table:${index}`,
      blockType: "table",
      title: table.headers.length > 0 ? `Visible table ${index + 1}` : null,
      summary: table.headers.length > 0 ? `Columns: ${table.headers.join(", ")}` : "Visible table",
      keywords: table.headers.slice(0, 8),
      headers: table.headers,
      rows: table.rows,
    })
  })

  return [...scriptedBlocks, ...derivedBlocks].slice(0, DOM_SEMANTIC_BLOCK_LIMIT)
}

function buildDomSnapshot(): AiChatDomSnapshot {
  if (typeof document === "undefined") {
    return { title: null, headings: [], textExcerpt: null, tables: [], actionableElements: [], semanticBlocks: [] }
  }

  const root = document.querySelector("main") ?? document.body
  const actionableElements = buildActionableElements(root)
  const headingNodes = Array.from(root.querySelectorAll("h1, h2, h3"))
  const headings = headingNodes
    .map((node) => normalizeText(node.textContent))
    .filter(Boolean)
    .slice(0, DOM_HEADING_LIMIT)

  const textRoot = root.cloneNode(true) as Element
  Array.from(textRoot.querySelectorAll("script, style, noscript")).forEach((node) => node.remove())
  const textExcerpt = normalizeText(textRoot.textContent).slice(0, DOM_TEXT_LIMIT) || null
  const tables: AiChatDomTableSnapshot[] = Array.from(root.querySelectorAll("table"))
    .slice(0, DOM_TABLE_LIMIT)
    .map((table) => {
      const headerCells = Array.from(table.querySelectorAll("thead th, tr:first-child th, tr:first-child td"))
        .map((cell) => normalizeText(cell.textContent))
        .filter(Boolean)
        .slice(0, DOM_TABLE_COL_LIMIT)

      const bodyRows = Array.from(table.querySelectorAll("tbody tr, tr"))
        .slice(1, DOM_TABLE_ROW_LIMIT + 1)
        .map((row) =>
          Array.from(row.querySelectorAll("th, td"))
            .map((cell) => normalizeText(cell.textContent))
            .filter(Boolean)
            .slice(0, DOM_TABLE_COL_LIMIT),
        )
        .filter((row) => row.length > 0)

      return {
        headers: headerCells,
        rows: bodyRows,
      }
    })
    .filter((table) => table.headers.length > 0 || table.rows.length > 0)
  const semanticBlocks = parseSemanticBlocks(root, tables, headings, textExcerpt)

  return {
    title: normalizeText(document.title) || null,
    headings,
    textExcerpt,
    tables,
    actionableElements,
    semanticBlocks,
  }
}

function mergeRegistrations(registrations: RegisteredStateMap): AiChatPageContextRegistration {
  const values = Object.values(registrations)
  if (values.length === 0) {
    return {}
  }

  const merged: AiChatPageContextRegistration = {
    entityRefs: [],
    filters: {},
    extra: {},
  }

  for (const value of values) {
    if (value.pageTitle) {
      merged.pageTitle = value.pageTitle
    }
    if (value.pageTypeHint) {
      merged.pageTypeHint = value.pageTypeHint
    }
    if (value.sessionId !== undefined) {
      merged.sessionId = value.sessionId
    }
    if (value.symbol) {
      merged.symbol = value.symbol
    }
    if (value.timeframe) {
      merged.timeframe = value.timeframe
    }
    if (value.activeTab) {
      merged.activeTab = value.activeTab
    }
    if (value.entityRefs?.length) {
      merged.entityRefs = [...(merged.entityRefs || []), ...value.entityRefs]
    }
    if (value.filters) {
      merged.filters = { ...(merged.filters || {}), ...value.filters }
    }
    if (value.extra) {
      merged.extra = { ...(merged.extra || {}), ...value.extra }
    }
  }
  merged.pageIntelligence = mergePageIntelligence(values.map((value) => value.pageIntelligence))

  if (!merged.entityRefs?.length) {
    delete merged.entityRefs
  }
  if (!merged.filters || Object.keys(merged.filters).length === 0) {
    delete merged.filters
  }
  if (!merged.extra || Object.keys(merged.extra).length === 0) {
    delete merged.extra
  }
  if (!merged.pageIntelligence) {
    delete merged.pageIntelligence
  }

  return merged
}

export function PageContextProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { authenticatedFetch, isAuthenticated, isLoading: authLoading } = useAuth()
  const [pageContext, setPageContext] = React.useState<AiChatPageContextPayload | null>(null)
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [registrations, setRegistrations] = React.useState<RegisteredStateMap>({})
  const [actionCallbacks, setActionCallbacks] = React.useState<Record<string, Record<string, (params: Record<string, unknown>) => void | Promise<void>>>>({})
  const [domVersion, setDomVersion] = React.useState(0)

  const registerPageContext = React.useCallback((id: string, registration: AiChatPageContextRegistration, callbacks?: Record<string, (params: Record<string, unknown>) => void | Promise<void>>) => {
    setRegistrations((current) => {
      const next = { ...current, [id]: registration }
      return next
    })
    if (callbacks) {
      setActionCallbacks((current) => ({ ...current, [id]: callbacks }))
    }
  }, [])

  const unregisterPageContext = React.useCallback((id: string) => {
    setRegistrations((current) => {
      if (!(id in current)) {
        return current
      }
      const next = { ...current }
      delete next[id]
      return next
    })
    setActionCallbacks((current) => {
      if (!(id in current)) return current
      const next = { ...current }
      delete next[id]
      return next
    })
  }, [])

  const executeAction = React.useCallback(async (actionId: string, params: Record<string, unknown>) => {
    for (const callbacks of Object.values(actionCallbacks)) {
      if (actionId in callbacks) {
        try {
          await callbacks[actionId](params)
          return true
        } catch (err) {
          console.error(`Failed to execute page action ${actionId}:`, err)
          throw err
        }
      }
    }
    console.warn(`No callback registered for page action ${actionId}`)
    return false
  }, [actionCallbacks])

  React.useEffect(() => {
    if (typeof document === "undefined") {
      return
    }

    let timeoutId: ReturnType<typeof setTimeout> | null = null
    const root = document.querySelector("main") ?? document.body
    if (!root) {
      return
    }

    const scheduleRefresh = () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = setTimeout(() => {
        setDomVersion((current) => current + 1)
      }, 200)
    }

    scheduleRefresh()
    const observer = new MutationObserver(() => {
      scheduleRefresh()
    })
    observer.observe(root, {
      childList: true,
      subtree: true,
      characterData: true,
    })

    return () => {
      observer.disconnect()
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [pathname])

  const mergedRegistration = React.useMemo(
    () => mergeRegistrations(registrations),
    [registrations],
  )

  React.useEffect(() => {
    if (authLoading || !isAuthenticated) {
      return
    }

    let isMounted = true

    async function loadContext() {
      setIsLoading(true)
      setError(null)
      try {
        const domSnapshot = buildDomSnapshot()
        const baselinePageIntelligence: AiChatPageIntelligence = {
          pageIdentity: {
            route: pathname || "/",
            pageType: mergedRegistration.pageTypeHint ?? null,
            title: mergedRegistration.pageTitle ?? domSnapshot.title ?? null,
            activeTab: mergedRegistration.activeTab ?? null,
          },
          primaryEntity: mergedRegistration.entityRefs?.[0] ?? null,
          selectedEntities: mergedRegistration.entityRefs ?? [],
          visibleTables: (domSnapshot.tables ?? []).map((table, index) => ({
            id: `dom_table_${index + 1}`,
            title: table.headers.length > 0 ? `Visible table ${index + 1}` : "Visible table",
            headers: table.headers,
            rows: table.rows,
            source: "dom_snapshot",
          })),
          filters: mergedRegistration.filters ?? {},
          freshness: {
            observedAt: new Date().toISOString(),
            stalenessSeconds: 0,
            source: "page_context_provider",
          },
        }
        const pageIntelligence = mergePageIntelligence([
          baselinePageIntelligence,
          mergedRegistration.pageIntelligence,
        ])
        const registeredSemanticBlocks = pageIntelligenceToSemanticBlocks(pageIntelligence)
        const semanticBlocks = [
          ...registeredSemanticBlocks,
          ...(domSnapshot.semanticBlocks ?? []),
        ]
        const response = await authenticatedFetch(`${API_URL}/api/ai-chat/context/resolve`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            route: pathname || "/",
            page_title: mergedRegistration.pageTitle ?? domSnapshot.title ?? undefined,
            page_state: {
              page_type_hint: mergedRegistration.pageTypeHint ?? null,
              session_id: mergedRegistration.sessionId ?? null,
              symbol: mergedRegistration.symbol ?? null,
              timeframe: mergedRegistration.timeframe ?? null,
              active_tab: mergedRegistration.activeTab ?? null,
              entity_refs: mergedRegistration.entityRefs ?? [],
              filters: mergedRegistration.filters ?? {},
              extra: mergedRegistration.extra ?? {},
              page_intelligence: pageIntelligence ?? null,
            },
            dom: {
              title: domSnapshot.title ?? null,
              headings: domSnapshot.headings,
              text_excerpt: domSnapshot.textExcerpt ?? null,
              tables: domSnapshot.tables ?? [],
              actionable_elements: domSnapshot.actionableElements ?? [],
              semantic_blocks: semanticBlocks,
            },
          }),
        })
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
  }, [authLoading, authenticatedFetch, isAuthenticated, mergedRegistration, pathname, domVersion])

  const value = React.useMemo<PageContextValue>(
    () => ({
      pageContext,
      isLoading,
      error,
      registerPageContext,
      unregisterPageContext,
      executeAction,
    }),
    [error, isLoading, pageContext, registerPageContext, unregisterPageContext, executeAction],
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
