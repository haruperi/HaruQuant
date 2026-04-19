"use client"

import { usePageContextValue } from "@/providers/PageContextProvider"

export function usePageContext() {
  return usePageContextValue()
}
