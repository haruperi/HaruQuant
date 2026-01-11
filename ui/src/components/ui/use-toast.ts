/**
 * Simple Toast Hook
 *
 * A basic toast notification hook for user feedback
 */

import { useState, useCallback } from 'react'

export type ToastVariant = 'default' | 'destructive' | 'success'

export interface Toast {
  id: string
  title?: string
  description?: string
  variant?: ToastVariant
}

interface ToastOptions {
  title?: string
  description?: string
  variant?: ToastVariant
}

const toasts: Toast[] = []
const listeners: Array<(toasts: Toast[]) => void> = []

function addToast(toast: Toast) {
  toasts.push(toast)
  listeners.forEach((listener) => listener([...toasts]))

  // Auto-remove after 5 seconds
  setTimeout(() => {
    removeToast(toast.id)
  }, 5000)
}

function removeToast(id: string) {
  const index = toasts.findIndex((t) => t.id === id)
  if (index > -1) {
    toasts.splice(index, 1)
    listeners.forEach((listener) => listener([...toasts]))
  }
}

function subscribe(listener: (toasts: Toast[]) => void) {
  listeners.push(listener)
  return () => {
    const index = listeners.indexOf(listener)
    if (index > -1) {
      listeners.splice(index, 1)
    }
  }
}

export function useToast() {
  const [, setToasts] = useState<Toast[]>([])

  const toast = useCallback((options: ToastOptions) => {
    const id = Math.random().toString(36).substring(7)
    addToast({
      id,
      ...options,
    })
  }, [])

  return { toast, toasts }
}

// Export for Toaster component
export { subscribe, removeToast }
