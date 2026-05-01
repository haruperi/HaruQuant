"use client"

import * as React from "react"

import type { AiChatPageActionAffordance } from "@/lib/ai-chat/contracts"
import { usePageContextValue } from "@/providers/PageContextProvider"

/**
 * Hook for pages to register allowed UI actions and their implementations for the AI assistant.
 * 
 * @param actions - List of actions the assistant is allowed to plan for this page.
 * @param callbacks - Implementation of each action by id.
 */
export function useRegisterPageActions(
  actions: AiChatPageActionAffordance[],
  callbacks?: Record<string, (params: any) => void | Promise<void>>
) {
  const { registerPageContext, unregisterPageContext } = usePageContextValue()
  const registrationId = React.useId()

  React.useEffect(() => {
    registerPageContext(
      registrationId,
      {
        pageIntelligence: {
          actionAffordances: actions,
        },
      },
      callbacks
    )
    return () => {
      unregisterPageContext(registrationId)
    }
  }, [actions, callbacks, registerPageContext, registrationId, unregisterPageContext])
}
