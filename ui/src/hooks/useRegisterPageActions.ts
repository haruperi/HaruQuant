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
  callbacks?: Record<string, (params: Record<string, unknown>) => void | Promise<void>>
) {
  const { registerPageContext, unregisterPageContext } = usePageContextValue()
  const registrationId = React.useId()

  // Stability: We stringify the actions to check for deep changes
  const actionsKey = JSON.stringify(actions)

  // Stability: We keep callbacks in a ref so we can use them in the effect
  // without triggering the effect when the literal object changes.
  const callbacksRef = React.useRef(callbacks)

  React.useEffect(() => {
    callbacksRef.current = callbacks
  }, [callbacks])

  React.useEffect(() => {
    registerPageContext(
      registrationId,
      {
        pageIntelligence: {
          actionAffordances: JSON.parse(actionsKey),
        },
      },
      callbacksRef.current
    )
    return () => {
      unregisterPageContext(registrationId)
    }
  }, [actionsKey, registerPageContext, registrationId, unregisterPageContext])
}
