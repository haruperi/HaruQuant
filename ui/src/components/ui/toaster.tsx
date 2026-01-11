/**
 * Toaster Component
 *
 * Displays toast notifications
 */

'use client'

import { useEffect, useState } from 'react'
import { subscribe, removeToast, type Toast } from './use-toast'
import { X } from 'lucide-react'

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    return subscribe(setToasts)
  }, [])

  return (
    <div className="fixed bottom-0 right-0 z-50 w-full max-w-md p-4 space-y-4 pointer-events-none sm:max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            pointer-events-auto w-full overflow-hidden rounded-lg shadow-lg ring-1 ring-black ring-opacity-5
            ${
              toast.variant === 'destructive'
                ? 'bg-red-50 border-red-200'
                : toast.variant === 'success'
                ? 'bg-green-50 border-green-200'
                : 'bg-white border-gray-200'
            }
            border animate-in slide-in-from-right
          `}
        >
          <div className="p-4">
            <div className="flex items-start">
              <div className="flex-1">
                {toast.title && (
                  <p
                    className={`
                      text-sm font-medium
                      ${
                        toast.variant === 'destructive'
                          ? 'text-red-800'
                          : toast.variant === 'success'
                          ? 'text-green-800'
                          : 'text-gray-900'
                      }
                    `}
                  >
                    {toast.title}
                  </p>
                )}
                {toast.description && (
                  <p
                    className={`
                      mt-1 text-sm
                      ${
                        toast.variant === 'destructive'
                          ? 'text-red-700'
                          : toast.variant === 'success'
                          ? 'text-green-700'
                          : 'text-gray-500'
                      }
                    `}
                  >
                    {toast.description}
                  </p>
                )}
              </div>
              <div className="ml-4 flex-shrink-0 flex">
                <button
                  onClick={() => removeToast(toast.id)}
                  className={`
                    inline-flex rounded-md
                    ${
                      toast.variant === 'destructive'
                        ? 'text-red-400 hover:text-red-500 focus:ring-red-500'
                        : toast.variant === 'success'
                        ? 'text-green-400 hover:text-green-500 focus:ring-green-500'
                        : 'text-gray-400 hover:text-gray-500 focus:ring-gray-500'
                    }
                    focus:outline-none focus:ring-2 focus:ring-offset-2
                  `}
                >
                  <span className="sr-only">Close</span>
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
