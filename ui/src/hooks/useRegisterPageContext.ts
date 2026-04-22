"use client"

import * as React from "react"

import type { AiChatPageContextRegistration } from "@/lib/ai-chat/contracts"
import { usePageContextValue } from "@/providers/PageContextProvider"

export function useRegisterPageContext(registration: AiChatPageContextRegistration) {
  const { registerPageContext, unregisterPageContext } = usePageContextValue()
  const registrationId = React.useId()

  React.useEffect(() => {
    registerPageContext(registrationId, registration)
    return () => {
      unregisterPageContext(registrationId)
    }
  }, [registerPageContext, registration, registrationId, unregisterPageContext])
}
