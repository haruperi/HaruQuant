"use client"

import * as React from "react"

import {
  createAiChatThread,
  deleteAiChatThread,
  exportAiChatThread,
  executeAiChatPaperActionDraft,
  getAiChatThread,
  listAiChatActionDrafts,
  listAiChatThreads,
  listAiChatSignalProposals,
  listAiChatTools,
  queueAiChatSignalProposalForReview,
  regenerateAiChatResponse,
  renameAiChatThread,
  requestAiChatActionDraftApproval,
  saveAiChatSignalProposalToWatchlist,
  searchAiChatThreads,
  streamAiChatResponse,
  updateAiChatThreadContext,
} from "@/lib/api/ai-chat"
import type {
  AiChatActionDraft,
  AiChatCostPolicyMetadata,
  AiChatMessage,
  AiChatPageContextPayload,
  AiChatResponseMetadata,
  AiChatResponseStyle,
  AiChatSignalProposal,
  AiChatSpecialistArtifact,
  AiChatStrategyCreatorMetadata,
  AiChatTelemetryMetadata,
  AiChatToolAttachment,
  AiChatToolDefinition,
  AiChatThreadDetail,
  AiChatThreadSummary,
} from "@/lib/ai-chat/contracts"
import { useAuth } from "@/lib/auth-context"
import { usePageContext } from "@/hooks/usePageContext"

type ChatRole = "user" | "assistant"

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  toolCalls?: string[]
  requestId?: string | null
  signalProposalId?: string | null
  signalProposal?: AiChatSignalProposal
  actionDraftId?: string | null
  actionDraft?: AiChatActionDraft
  attachedTools?: AiChatToolAttachment[]
  strategyCreator?: AiChatStrategyCreatorMetadata
  responseMode?: string
  responseStyle?: string
  taskClass?: string
  domainFocus?: string
  answerMode?: string
  generationSource?: string
  providerName?: string | null
  model?: string
  conversationPlanId?: string
  clarificationRequired?: boolean
  activeTopic?: string | null
  specialistAgentsUsed?: string[]
  specialistArtifacts?: AiChatSpecialistArtifact[]
  telemetry?: AiChatTelemetryMetadata
  costPolicy?: AiChatCostPolicyMetadata
  status?: "ready" | "pending"
}

export interface ChatThreadListItem {
  threadId: string
  title: string
  updatedAt: string
  pageType?: string | null
}

interface ChatWidgetStoreValue {
  isOpen: boolean
  isHydrated: boolean
  isInitializing: boolean
  isOnline: boolean
  isRestoring: boolean
  isStreaming: boolean
  isManagingThreads: boolean
  availableTools: AiChatToolDefinition[]
  selectedToolIds: string[]
  draft: string
  messages: ChatMessage[]
  threads: ChatThreadListItem[]
  threadSearch: string
  threadId: string | null
  threadTitle: string
  activeResponseStatus: string | null
  error: string | null
  open: () => void
  close: () => void
  toggle: () => void
  setDraft: (value: string) => void
  setThreadSearch: (value: string) => void
  toggleTool: (toolId: string) => void
  createNewThread: () => Promise<void>
  selectThread: (value: string) => Promise<void>
  renameThread: (value: string, targetThreadId?: string) => Promise<void>
  deleteThread: (targetThreadId?: string) => Promise<void>
  exportThread: (targetThreadId?: string) => Promise<void>
  saveSignalProposalToWatchlist: (proposalId: string) => Promise<void>
  queueSignalProposalForReview: (proposalId: string) => Promise<void>
  requestActionDraftApproval: (draftId: string) => Promise<void>
  executePaperActionDraft: (draftId: string) => Promise<void>
  submitDraft: () => Promise<void>
  regenerateLastResponse: () => Promise<void>
  cancelStream: () => void
}

const STORAGE_KEYS = {
  open: "haruquant.ai_chat.open",
  draft: "haruquant.ai_chat.draft",
  activeThreadId: "haruquant.ai_chat.active_thread_id",
} as const

const DEFAULT_THREAD_TITLE = "New conversation"
const ChatWidgetStoreContext = React.createContext<ChatWidgetStoreValue | null>(null)
const AI_CHAT_RESPONSE_STYLES: ReadonlySet<AiChatResponseStyle> = new Set([
  "summary",
  "compare",
  "warning",
  "recommendation",
  "diagnostic",
  "clarification",
])

function mapApiMessage(
  message: AiChatMessage,
  metadataByRequestId: Record<string, AiChatResponseMetadata>,
): ChatMessage {
  const responseMetadata = message.request_id ? metadataByRequestId[message.request_id] : undefined
  return {
    id: message.message_id,
    role: message.role === "assistant" ? "assistant" : "user",
    content: message.content,
    createdAt: message.created_at,
    toolCalls: message.tool_calls,
    requestId: message.request_id,
    signalProposalId: message.signal_proposal_id,
    actionDraftId: message.action_draft_id,
    signalProposal: message.signal_proposal_id ? responseMetadata?.signal_proposal : undefined,
    actionDraft: message.action_draft_id ? responseMetadata?.action_draft : undefined,
    responseMode: responseMetadata?.response_mode,
    responseStyle: responseMetadata?.response_style,
    taskClass: responseMetadata?.task_class,
    domainFocus: responseMetadata?.domain_focus,
    answerMode: responseMetadata?.answer_mode,
    generationSource: responseMetadata?.generation_source,
    providerName: responseMetadata?.provider_name,
    model: responseMetadata?.model,
    conversationPlanId: responseMetadata?.conversation_plan_id,
    clarificationRequired: responseMetadata?.clarification_required,
    activeTopic: responseMetadata?.active_topic,
    specialistAgentsUsed: responseMetadata?.specialist_agents_used,
    specialistArtifacts: responseMetadata?.specialist_artifacts,
    attachedTools: responseMetadata?.attached_tools,
    strategyCreator: responseMetadata?.strategy_creator,
    telemetry: responseMetadata?.telemetry,
    costPolicy: responseMetadata?.cost_policy,
    status: "ready",
  }
}

function mapThreadSummary(thread: AiChatThreadSummary): ChatThreadListItem {
  return {
    threadId: thread.thread_id,
    title: thread.title,
    updatedAt: thread.last_message_at ?? thread.updated_at,
    pageType: thread.current_page_type,
  }
}

function makePendingAssistant(): ChatMessage {
  const idSuffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}_${Math.random().toString(16).slice(2)}`
  return {
    id: `assistant_pending_${idSuffix}`,
    role: "assistant",
    content: "",
    createdAt: new Date().toISOString(),
    status: "pending",
  }
}

function buildRuntimeContextPayload(pageContext: AiChatPageContextPayload | null) {
  const payload = pageContext?.payload as Record<string, unknown> | undefined
  return {
    context_route: pageContext?.route,
    context_page_title: pageContext?.page_title ?? undefined,
    context_session_id: typeof payload?.session_id === "number" ? payload.session_id : undefined,
    context_symbol: typeof payload?.symbol === "string" ? payload.symbol : undefined,
    context_timeframe: typeof payload?.timeframe === "string" ? payload.timeframe : undefined,
    context_dom: payload?.dom && typeof payload.dom === "object" ? payload.dom as Record<string, unknown> : undefined,
  }
}

function extractResponseMetadata(payload: Record<string, unknown>): AiChatResponseMetadata | null {
  const requestId = typeof payload.request_id === "string" ? payload.request_id : undefined
  if (!requestId) {
    return null
  }
  return {
    request_id: requestId,
    response_mode: typeof payload.response_mode === "string" ? payload.response_mode as AiChatResponseMetadata["response_mode"] : undefined,
    response_style:
      typeof payload.response_style === "string" && AI_CHAT_RESPONSE_STYLES.has(payload.response_style as AiChatResponseStyle)
        ? payload.response_style as AiChatResponseStyle
        : undefined,
    task_class: typeof payload.task_class === "string" ? payload.task_class : undefined,
    domain_focus: typeof payload.domain_focus === "string" ? payload.domain_focus : undefined,
    answer_mode: typeof payload.answer_mode === "string" ? payload.answer_mode : undefined,
    generation_source: typeof payload.generation_source === "string" ? payload.generation_source : undefined,
    provider_name: typeof payload.provider_name === "string" ? payload.provider_name : undefined,
    model: typeof payload.model === "string" ? payload.model : undefined,
    tools_used: Array.isArray(payload.tools_used) ? payload.tools_used.filter((value): value is string => typeof value === "string") : undefined,
    conversation_plan_id: typeof payload.conversation_plan_id === "string" ? payload.conversation_plan_id : undefined,
    clarification_required: typeof payload.clarification_required === "boolean" ? payload.clarification_required : undefined,
    active_topic: typeof payload.active_topic === "string" ? payload.active_topic : undefined,
    specialist_agents_used: Array.isArray(payload.specialist_agents_used)
      ? payload.specialist_agents_used.filter((value): value is string => typeof value === "string")
      : undefined,
    specialist_artifacts: Array.isArray(payload.specialist_artifacts)
      ? payload.specialist_artifacts.filter((value): value is AiChatSpecialistArtifact => !!value && typeof value === "object") as AiChatSpecialistArtifact[]
      : undefined,
    telemetry:
      payload.telemetry && typeof payload.telemetry === "object"
        ? payload.telemetry as AiChatTelemetryMetadata
        : undefined,
    cost_policy:
      payload.cost_policy && typeof payload.cost_policy === "object"
        ? payload.cost_policy as AiChatCostPolicyMetadata
        : undefined,
    signal_proposal_id: typeof payload.signal_proposal_id === "string" ? payload.signal_proposal_id : undefined,
    action_draft_id: typeof payload.action_draft_id === "string" ? payload.action_draft_id : undefined,
    signal_proposal:
      payload.signal_proposal && typeof payload.signal_proposal === "object"
        ? payload.signal_proposal as AiChatSignalProposal
        : undefined,
    action_draft:
      payload.action_draft && typeof payload.action_draft === "object"
        ? payload.action_draft as AiChatActionDraft
        : undefined,
    attached_tools: Array.isArray(payload.attached_tools)
      ? payload.attached_tools.filter((value): value is AiChatToolAttachment => !!value && typeof value === "object") as AiChatToolAttachment[]
      : undefined,
    strategy_creator:
      payload.strategy_creator && typeof payload.strategy_creator === "object"
        ? payload.strategy_creator as AiChatStrategyCreatorMetadata
        : undefined,
  }
}

export function ChatWidgetStoreProvider({ children }: { children: React.ReactNode }) {
  const { authenticatedFetch, isAuthenticated, isLoading } = useAuth()
  const { pageContext } = usePageContext()
  const [isOpen, setIsOpen] = React.useState(false)
  const [draft, setDraftState] = React.useState("")
  const [messages, setMessages] = React.useState<ChatMessage[]>([])
  const [threads, setThreads] = React.useState<ChatThreadListItem[]>([])
  const [availableTools, setAvailableTools] = React.useState<AiChatToolDefinition[]>([])
  const [selectedToolIds, setSelectedToolIds] = React.useState<string[]>([])
  const [isHydrated, setIsHydrated] = React.useState(false)
  const [isInitializing, setIsInitializing] = React.useState(false)
  const [hasOpenedOnce, setHasOpenedOnce] = React.useState(false)
  const [isOnline, setIsOnline] = React.useState(true)
  const [isRestoring, setIsRestoring] = React.useState(false)
  const [isStreaming, setIsStreaming] = React.useState(false)
  const [isManagingThreads, setIsManagingThreads] = React.useState(false)
  const [threadSearch, setThreadSearchState] = React.useState("")
  const [threadId, setThreadId] = React.useState<string | null>(null)
  const [threadTitle, setThreadTitle] = React.useState(DEFAULT_THREAD_TITLE)
  const [activeResponseStatus, setActiveResponseStatus] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const abortControllerRef = React.useRef<AbortController | null>(null)
  const responseMetadataRef = React.useRef<Record<string, AiChatResponseMetadata>>({})
  const signalProposalMapRef = React.useRef<Record<string, AiChatSignalProposal>>({})
  const actionDraftMapRef = React.useRef<Record<string, AiChatActionDraft>>({})
  const lastSyncedContextRef = React.useRef<string | null>(null)

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    setIsOpen(window.localStorage.getItem(STORAGE_KEYS.open) === "true")
    setDraftState(window.localStorage.getItem(STORAGE_KEYS.draft) ?? "")
    setThreadId(window.localStorage.getItem(STORAGE_KEYS.activeThreadId))
    setIsOnline(window.navigator.onLine)
    setIsHydrated(true)
  }, [])

  React.useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return
    }
    window.localStorage.setItem(STORAGE_KEYS.open, String(isOpen))
  }, [isHydrated, isOpen])

  React.useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return
    }
    window.localStorage.setItem(STORAGE_KEYS.draft, draft)
  }, [draft, isHydrated])

  React.useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return
    }
    if (threadId) {
      window.localStorage.setItem(STORAGE_KEYS.activeThreadId, threadId)
      return
    }
    window.localStorage.removeItem(STORAGE_KEYS.activeThreadId)
  }, [isHydrated, threadId])

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    const onOnline = () => setIsOnline(true)
    const onOffline = () => setIsOnline(false)

    window.addEventListener("online", onOnline)
    window.addEventListener("offline", onOffline)

    return () => {
      window.removeEventListener("online", onOnline)
      window.removeEventListener("offline", onOffline)
    }
  }, [])

  const syncThread = React.useCallback((thread: AiChatThreadDetail) => {
    setThreadId(thread.thread_id)
    setThreadTitle(thread.title)
    setMessages(
      thread.messages
        .filter((message) => message.role === "user" || message.role === "assistant")
        .map((message) => {
          const metadata = message.request_id ? responseMetadataRef.current[message.request_id] : undefined
          const signalProposal =
            message.signal_proposal_id
              ? signalProposalMapRef.current[message.signal_proposal_id] ?? metadata?.signal_proposal
              : undefined
          const actionDraft =
            message.action_draft_id
              ? actionDraftMapRef.current[message.action_draft_id] ?? metadata?.action_draft
              : undefined
          return {
            ...mapApiMessage(message, responseMetadataRef.current),
            signalProposal: signalProposal,
            actionDraft: actionDraft,
          }
        }),
    )
  }, [])

  const rememberResponseMetadata = React.useCallback((payload: Record<string, unknown>) => {
    const metadata = extractResponseMetadata(payload)
    if (!metadata?.request_id) {
      return
    }
    responseMetadataRef.current[metadata.request_id] = metadata
    if (metadata.signal_proposal?.proposal_id) {
      signalProposalMapRef.current[metadata.signal_proposal.proposal_id] = metadata.signal_proposal
    }
    if (metadata.action_draft?.draft_id) {
      actionDraftMapRef.current[metadata.action_draft.draft_id] = metadata.action_draft
    }
  }, [])

  const refreshSignalProposals = React.useCallback(async (activeThreadId: string) => {
    if (!isAuthenticated) {
      return
    }
    const proposals = await listAiChatSignalProposals(authenticatedFetch, activeThreadId)
    signalProposalMapRef.current = Object.fromEntries(
      proposals.map((proposal) => [proposal.proposal_id, proposal]),
    )
  }, [authenticatedFetch, isAuthenticated])

  const refreshActionDrafts = React.useCallback(async (activeThreadId: string) => {
    if (!isAuthenticated) {
      return
    }
    const drafts = await listAiChatActionDrafts(authenticatedFetch, activeThreadId)
    actionDraftMapRef.current = Object.fromEntries(
      drafts.map((draft) => [draft.draft_id, draft]),
    )
  }, [authenticatedFetch, isAuthenticated])

  const refreshThreadList = React.useCallback(async (query?: string) => {
    if (!isAuthenticated) {
      setThreads([])
      return
    }
    const listed = query && query.trim().length > 0
      ? await searchAiChatThreads(authenticatedFetch, query.trim())
      : await listAiChatThreads(authenticatedFetch)
    setThreads(listed.map(mapThreadSummary))
  }, [authenticatedFetch, isAuthenticated])

  const ensureThread = React.useCallback(async () => {
    if (!isAuthenticated) {
      return null
    }

    if (threadId) {
      const existing = await getAiChatThread(authenticatedFetch, threadId)
      await refreshSignalProposals(threadId)
      await refreshActionDrafts(threadId)
      syncThread(existing)
      return existing
    }

    const listed = await listAiChatThreads(authenticatedFetch)
    setThreads(listed.map(mapThreadSummary))
    const selected = listed[0]

    if (selected) {
      const existing = await getAiChatThread(authenticatedFetch, selected.thread_id)
      await refreshSignalProposals(selected.thread_id)
      await refreshActionDrafts(selected.thread_id)
      syncThread(existing)
      return existing
    }

    const created = await createAiChatThread(authenticatedFetch, {
      current_route: pageContext?.route,
      current_page_type: pageContext?.page_type,
      active_context_revision: pageContext?.context_revision,
    })
    signalProposalMapRef.current = {}
    syncThread(created)
    await refreshThreadList()
    return created
  }, [
    authenticatedFetch,
    isAuthenticated,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    refreshThreadList,
    refreshActionDrafts,
    refreshSignalProposals,
    syncThread,
    threadId,
  ])

  React.useEffect(() => {
    if (!isHydrated || isLoading || !isAuthenticated) {
      return
    }

    let isMounted = true

    async function restoreThread() {
      setIsRestoring(true)
      setError(null)
      try {
        const restored = await ensureThread()
        if (!isMounted || !restored) {
          return
        }
        await refreshThreadList(threadSearch)
      } catch (restoreError) {
        console.error("Failed to restore AI chat thread:", restoreError)
        if (isMounted) {
          setError("Unable to restore conversation history.")
        }
      } finally {
        if (isMounted) {
          setIsRestoring(false)
        }
      }
    }

    void restoreThread()

    return () => {
      isMounted = false
    }
  }, [
    authenticatedFetch,
    ensureThread,
    isAuthenticated,
    isHydrated,
    isLoading,
    refreshThreadList,
    threadSearch,
  ])

  React.useEffect(() => {
    if (!isHydrated || isLoading || !isAuthenticated || !threadId) {
      return
    }

    const nextSignature = JSON.stringify({
      threadId,
      route: pageContext?.route ?? null,
      pageType: pageContext?.page_type ?? null,
      contextRevision: pageContext?.context_revision ?? null,
    })

    if (lastSyncedContextRef.current === nextSignature) {
      return
    }

    let isCancelled = false
    const timeoutId = window.setTimeout(async () => {
      try {
        await updateAiChatThreadContext(authenticatedFetch, threadId, {
          current_route: pageContext?.route,
          current_page_type: pageContext?.page_type,
          active_context_revision: pageContext?.context_revision,
        })
        if (!isCancelled) {
          lastSyncedContextRef.current = nextSignature
        }
      } catch (contextError) {
        console.error("Failed to sync AI chat thread context:", contextError)
      }
    }, 300)

    return () => {
      isCancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isHydrated,
    isLoading,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    threadId,
  ])

  React.useEffect(() => {
    if (!isAuthenticated || !isHydrated) {
      return
    }
    void refreshThreadList(threadSearch)
  }, [isAuthenticated, isHydrated, refreshThreadList, threadSearch])

  React.useEffect(() => {
    if (!isAuthenticated || !isHydrated) {
      return
    }

    let isMounted = true
    async function loadTools() {
      try {
        const tools = await listAiChatTools(authenticatedFetch)
        if (isMounted) {
          setAvailableTools(tools)
        }
      } catch (toolError) {
        console.error("Failed to load AI chat tools:", toolError)
      }
    }

    void loadTools()

    return () => {
      isMounted = false
    }
  }, [authenticatedFetch, isAuthenticated, isHydrated])

  const beginInitialization = React.useCallback(() => {
    if (hasOpenedOnce) {
      return
    }
    setHasOpenedOnce(true)
    setIsInitializing(true)
    window.setTimeout(() => setIsInitializing(false), 350)
  }, [hasOpenedOnce])

  const open = React.useCallback(() => {
    setIsOpen(true)
    if (typeof window !== "undefined") {
      beginInitialization()
    }
  }, [beginInitialization])

  const close = React.useCallback(() => {
    setIsOpen(false)
  }, [])

  const toggle = React.useCallback(() => {
    setIsOpen((current) => {
      const next = !current
      if (next && typeof window !== "undefined") {
        beginInitialization()
      }
      return next
    })
  }, [beginInitialization])

  const setDraft = React.useCallback((value: string) => {
    setDraftState(value)
  }, [])

  const setThreadSearch = React.useCallback((value: string) => {
    setThreadSearchState(value)
  }, [])

  const toggleTool = React.useCallback((toolId: string) => {
    setSelectedToolIds((current) =>
      current.includes(toolId)
        ? current.filter((selected) => selected !== toolId)
        : [...current, toolId],
    )
  }, [])

  const cancelStream = React.useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
    setActiveResponseStatus(null)
  }, [])

  const createNewThread = React.useCallback(async () => {
    if (!isAuthenticated || isStreaming) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      const created = await createAiChatThread(authenticatedFetch, {
        current_route: pageContext?.route,
        current_page_type: pageContext?.page_type,
        active_context_revision: pageContext?.context_revision,
      })
      signalProposalMapRef.current = {}
      actionDraftMapRef.current = {}
      syncThread(created)
      setMessages([])
      setDraftState("")
      await refreshThreadList(threadSearch)
    } catch (threadError) {
      console.error("Failed to create AI chat thread:", threadError)
      setError("Unable to create a new conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isStreaming,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    refreshThreadList,
    syncThread,
    threadSearch,
  ])

  const selectThread = React.useCallback(async (value: string) => {
    if (!isAuthenticated || isStreaming) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      const selected = await getAiChatThread(authenticatedFetch, value)
      await refreshSignalProposals(value)
      await refreshActionDrafts(value)
      syncThread(selected)
      await updateAiChatThreadContext(authenticatedFetch, value, {
        current_route: pageContext?.route,
        current_page_type: pageContext?.page_type,
        active_context_revision: pageContext?.context_revision,
      })
    } catch (threadError) {
      console.error("Failed to select AI chat thread:", threadError)
      setError("Unable to load the selected conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isStreaming,
    pageContext?.context_revision,
    pageContext?.page_type,
    pageContext?.route,
    syncThread,
    refreshSignalProposals,
    refreshActionDrafts,
  ])

  const renameThread = React.useCallback(async (value: string, targetThreadId?: string) => {
    const selectedThreadId = targetThreadId ?? threadId
    if (!selectedThreadId || !isAuthenticated) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      const renamed = await renameAiChatThread(authenticatedFetch, selectedThreadId, { title: value })
      if (selectedThreadId === threadId) {
        syncThread(renamed)
      }
      await refreshThreadList(threadSearch)
    } catch (threadError) {
      console.error("Failed to rename AI chat thread:", threadError)
      setError("Unable to rename the conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [authenticatedFetch, isAuthenticated, refreshThreadList, syncThread, threadId, threadSearch])

  const deleteThread = React.useCallback(async (targetThreadId?: string) => {
    const selectedThreadId = targetThreadId ?? threadId
    if (!selectedThreadId || !isAuthenticated || isStreaming) {
      return
    }
    setIsManagingThreads(true)
    setError(null)
    try {
      await deleteAiChatThread(authenticatedFetch, selectedThreadId)
      const deletedActiveThread = selectedThreadId === threadId
      if (deletedActiveThread) {
        setThreadId(null)
        setThreadTitle(DEFAULT_THREAD_TITLE)
        setMessages([])
        signalProposalMapRef.current = {}
        actionDraftMapRef.current = {}
      }
      await refreshThreadList(threadSearch)
      if (deletedActiveThread) {
        const listed = threadSearch.trim().length > 0
          ? await searchAiChatThreads(authenticatedFetch, threadSearch.trim())
          : await listAiChatThreads(authenticatedFetch)
        const fallback = listed[0]
        if (fallback) {
          const selected = await getAiChatThread(authenticatedFetch, fallback.thread_id)
          await refreshSignalProposals(fallback.thread_id)
          await refreshActionDrafts(fallback.thread_id)
          syncThread(selected)
        }
      }
    } catch (threadError) {
      console.error("Failed to delete AI chat thread:", threadError)
      setError("Unable to delete the conversation.")
    } finally {
      setIsManagingThreads(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isStreaming,
    refreshThreadList,
    refreshSignalProposals,
    refreshActionDrafts,
    syncThread,
    threadId,
    threadSearch,
  ])

  const saveSignalProposalToWatchlist = React.useCallback(async (proposalId: string) => {
    if (!threadId || !isAuthenticated) {
      return
    }
    setError(null)
    try {
      const updated = await saveAiChatSignalProposalToWatchlist(authenticatedFetch, threadId, proposalId)
      signalProposalMapRef.current[proposalId] = updated
      const refreshed = await getAiChatThread(authenticatedFetch, threadId)
      syncThread(refreshed)
      setActiveResponseStatus(`Saved ${updated.symbol} signal proposal to watchlist.`)
    } catch (proposalError) {
      console.error("Failed to save signal proposal to watchlist:", proposalError)
      setError("Unable to save signal proposal to watchlist.")
    }
  }, [authenticatedFetch, isAuthenticated, syncThread, threadId])

  const queueSignalProposalForReview = React.useCallback(async (proposalId: string) => {
    if (!threadId || !isAuthenticated) {
      return
    }
    setError(null)
    try {
      const updated = await queueAiChatSignalProposalForReview(authenticatedFetch, threadId, proposalId)
      signalProposalMapRef.current[proposalId] = updated
      const refreshed = await getAiChatThread(authenticatedFetch, threadId)
      syncThread(refreshed)
      setActiveResponseStatus(`Queued ${updated.symbol} signal proposal for review.`)
    } catch (proposalError) {
      console.error("Failed to queue signal proposal for review:", proposalError)
      setError("Unable to queue signal proposal for review.")
    }
  }, [authenticatedFetch, isAuthenticated, syncThread, threadId])

  const requestActionDraftApproval = React.useCallback(async (draftId: string) => {
    if (!threadId || !isAuthenticated) {
      return
    }
    setError(null)
    try {
      const updated = await requestAiChatActionDraftApproval(authenticatedFetch, threadId, draftId)
      actionDraftMapRef.current[draftId] = updated
      const refreshed = await getAiChatThread(authenticatedFetch, threadId)
      syncThread(refreshed)
      setActiveResponseStatus(`Requested approval for ${updated.title}.`)
    } catch (draftError) {
      console.error("Failed to request action draft approval:", draftError)
      setError("Unable to request approval for action draft.")
    }
  }, [authenticatedFetch, isAuthenticated, syncThread, threadId])

  const executePaperActionDraft = React.useCallback(async (draftId: string) => {
    if (!threadId || !isAuthenticated) {
      return
    }
    setError(null)
    try {
      const result = await executeAiChatPaperActionDraft(authenticatedFetch, threadId, draftId)
      actionDraftMapRef.current[draftId] = result.action_draft
      const refreshed = await getAiChatThread(authenticatedFetch, threadId)
      syncThread(refreshed)
      setActiveResponseStatus(`Paper execution completed for ${result.action_draft.title}.`)
    } catch (draftError) {
      console.error("Failed to execute paper action draft:", draftError)
      setError(draftError instanceof Error ? draftError.message : "Unable to execute paper action draft.")
    }
  }, [authenticatedFetch, isAuthenticated, syncThread, threadId])

  const exportThread = React.useCallback(async (targetThreadId?: string) => {
    const selectedThreadId = targetThreadId ?? threadId
    if (!selectedThreadId || !isAuthenticated) {
      return
    }
    setError(null)
    try {
      const exported = await exportAiChatThread(authenticatedFetch, selectedThreadId, "markdown")
      if (typeof window !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(exported)
      }
      setActiveResponseStatus("Conversation export copied to clipboard.")
    } catch (threadError) {
      console.error("Failed to export AI chat thread:", threadError)
      setError("Unable to export the conversation.")
    }
  }, [authenticatedFetch, isAuthenticated, threadId])

  const submitDraft = React.useCallback(async () => {
    const trimmed = draft.trim()
    if (!trimmed || !isOnline || !isAuthenticated || isStreaming) {
      return
    }

    setError(null)
    const pendingAssistant = makePendingAssistant()
    setMessages((current) => [
      ...current,
      {
        id: `user_local_${Date.now()}`,
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
        status: "ready",
      },
      pendingAssistant,
    ])
    setDraftState("")
    setIsStreaming(true)
    setActiveResponseStatus("Streaming response...")
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const activeThread = await ensureThread()
      if (!activeThread) {
        throw new Error("No active thread available")
      }

      await streamAiChatResponse(
        authenticatedFetch,
        activeThread.thread_id,
        {
          prompt: trimmed,
          ...buildRuntimeContextPayload(pageContext),
          attached_tools: selectedToolIds,
        },
        {
          onMeta: (payload) => {
            rememberResponseMetadata(payload)
            const metadata = extractResponseMetadata(payload)
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                    ? {
                        ...message,
                      responseMode: metadata?.response_mode,
                      responseStyle: metadata?.response_style,
                      taskClass: metadata?.task_class,
                      domainFocus: metadata?.domain_focus,
                      answerMode: metadata?.answer_mode,
                      generationSource: metadata?.generation_source,
                      providerName: metadata?.provider_name,
                      model: metadata?.model,
                      conversationPlanId: metadata?.conversation_plan_id,
                      clarificationRequired: metadata?.clarification_required,
                      activeTopic: metadata?.active_topic,
                      specialistAgentsUsed: metadata?.specialist_agents_used,
                      specialistArtifacts: metadata?.specialist_artifacts,
                      attachedTools: metadata?.attached_tools,
                      strategyCreator: metadata?.strategy_creator,
                      telemetry: metadata?.telemetry,
                      costPolicy: metadata?.cost_policy,
                    }
                  : message,
              ),
            )
            const responseStyle = metadata?.response_style ?? "summary"
            const sourceLabel = metadata?.generation_source === "llm_runtime"
              ? `${metadata.provider_name ?? "runtime"} model`
              : "fallback mode"
            setActiveResponseStatus(`Assistant is responding with ${sourceLabel} (${responseStyle}).`)
          },
          onToken: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                  ? {
                      ...message,
                      content: `${message.content}${delta}`,
                    }
                  : message,
              ),
            )
          },
          onDone: async () => {
            const refreshed = await getAiChatThread(authenticatedFetch, activeThread.thread_id)
            await refreshSignalProposals(activeThread.thread_id)
            await refreshActionDrafts(activeThread.thread_id)
            syncThread(refreshed)
            await refreshThreadList(threadSearch)
            setActiveResponseStatus("Response complete.")
          },
          onError: (message) => {
            setError(message)
            setActiveResponseStatus(null)
          },
        },
        controller.signal,
      )
    } catch (submitError) {
      if (submitError instanceof DOMException && submitError.name === "AbortError") {
        setError("Response stopped.")
      } else {
        console.error("Failed to stream AI chat response:", submitError)
        setError("AI response failed. Draft was restored.")
      }
      setDraftState(trimmed)
      setMessages((current) => current.filter((message) => message.id !== pendingAssistant.id))
      return
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [
    authenticatedFetch,
    draft,
    ensureThread,
    isAuthenticated,
    isOnline,
    isStreaming,
    pageContext,
    refreshThreadList,
    refreshSignalProposals,
    refreshActionDrafts,
    rememberResponseMetadata,
    selectedToolIds,
    syncThread,
    threadSearch,
  ])

  const regenerateLastResponse = React.useCallback(async () => {
    if (!threadId || !isAuthenticated || !isOnline || isStreaming) {
      return
    }

    setError(null)
    const pendingAssistant = makePendingAssistant()
    setMessages((current) => [...current, pendingAssistant])
    setIsStreaming(true)
    setActiveResponseStatus("Regenerating last response...")
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      await regenerateAiChatResponse(
        authenticatedFetch,
        threadId,
        {
          ...buildRuntimeContextPayload(pageContext),
          attached_tools: selectedToolIds,
        },
        {
          onMeta: (payload) => {
            rememberResponseMetadata(payload)
            const metadata = extractResponseMetadata(payload)
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                    ? {
                        ...message,
                      responseMode: metadata?.response_mode,
                      responseStyle: metadata?.response_style,
                      taskClass: metadata?.task_class,
                      domainFocus: metadata?.domain_focus,
                      answerMode: metadata?.answer_mode,
                      generationSource: metadata?.generation_source,
                      providerName: metadata?.provider_name,
                      model: metadata?.model,
                      conversationPlanId: metadata?.conversation_plan_id,
                      clarificationRequired: metadata?.clarification_required,
                      activeTopic: metadata?.active_topic,
                      specialistAgentsUsed: metadata?.specialist_agents_used,
                      specialistArtifacts: metadata?.specialist_artifacts,
                      attachedTools: metadata?.attached_tools,
                      strategyCreator: metadata?.strategy_creator,
                      telemetry: metadata?.telemetry,
                      costPolicy: metadata?.cost_policy,
                    }
                  : message,
              ),
            )
            const responseStyle = metadata?.response_style ?? "summary"
            const sourceLabel = metadata?.generation_source === "llm_runtime"
              ? `${metadata.provider_name ?? "runtime"} model`
              : "fallback mode"
            setActiveResponseStatus(`Regenerated ${responseStyle} response in progress with ${sourceLabel}.`)
          },
          onToken: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === pendingAssistant.id
                  ? {
                      ...message,
                      content: `${message.content}${delta}`,
                    }
                  : message,
              ),
            )
          },
          onDone: async () => {
            const refreshed = await getAiChatThread(authenticatedFetch, threadId)
            await refreshSignalProposals(threadId)
            await refreshActionDrafts(threadId)
            syncThread(refreshed)
            await refreshThreadList(threadSearch)
            setActiveResponseStatus("Regenerated response complete.")
          },
          onError: (message) => {
            setError(message)
            setActiveResponseStatus(null)
          },
        },
        controller.signal,
      )
    } catch (submitError) {
      if (!(submitError instanceof DOMException && submitError.name === "AbortError")) {
        console.error("Failed to regenerate AI chat response:", submitError)
        setError("Unable to regenerate the last response.")
      }
      setMessages((current) => current.filter((message) => message.id !== pendingAssistant.id))
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [
    authenticatedFetch,
    isAuthenticated,
    isOnline,
    isStreaming,
    pageContext,
    refreshThreadList,
    refreshSignalProposals,
    refreshActionDrafts,
    rememberResponseMetadata,
    selectedToolIds,
    syncThread,
    threadId,
    threadSearch,
  ])

  React.useEffect(() => () => {
    abortControllerRef.current?.abort()
  }, [])

  const value = React.useMemo<ChatWidgetStoreValue>(
    () => ({
      isOpen,
      isHydrated,
      isInitializing,
      isOnline,
      isRestoring,
      isStreaming,
      isManagingThreads,
      availableTools,
      selectedToolIds,
      draft,
      messages,
      threads,
      threadSearch,
      threadId,
      threadTitle,
      activeResponseStatus,
      error,
      open,
      close,
      toggle,
      setDraft,
      setThreadSearch,
      toggleTool,
      createNewThread,
      selectThread,
      renameThread,
      deleteThread,
      exportThread,
      saveSignalProposalToWatchlist,
      queueSignalProposalForReview,
      requestActionDraftApproval,
      executePaperActionDraft,
      submitDraft,
      regenerateLastResponse,
      cancelStream,
    }),
    [
      activeResponseStatus,
      availableTools,
      cancelStream,
      close,
      createNewThread,
      deleteThread,
      draft,
      error,
      exportThread,
      isHydrated,
      isInitializing,
      isManagingThreads,
      isOnline,
      isOpen,
      isRestoring,
      isStreaming,
      messages,
      open,
      queueSignalProposalForReview,
      regenerateLastResponse,
      renameThread,
      executePaperActionDraft,
      requestActionDraftApproval,
      saveSignalProposalToWatchlist,
      setDraft,
      setThreadSearch,
      selectedToolIds,
      selectThread,
      submitDraft,
      threadId,
      threadSearch,
      threadTitle,
      threads,
      toggle,
      toggleTool,
    ],
  )

  return (
    <ChatWidgetStoreContext.Provider value={value}>
      {children}
    </ChatWidgetStoreContext.Provider>
  )
}

export function useChatWidgetStore() {
  const context = React.useContext(ChatWidgetStoreContext)
  if (!context) {
    throw new Error("useChatWidgetStore must be used within ChatWidgetStoreProvider")
  }
  return context
}
