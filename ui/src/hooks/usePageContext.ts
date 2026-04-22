"use client"

import { usePageContextValue } from "@/providers/PageContextProvider"
export { useRegisterPageContext } from "@/hooks/useRegisterPageContext"

export function usePageContext() {
  return usePageContextValue()
}
