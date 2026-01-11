"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { AlertTriangle, RefreshCw } from "lucide-react"

interface ErrorBoundaryProps {
  children: React.ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo)
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background p-4 text-center">
          <div className="rounded-full bg-red-100 p-3 dark:bg-red-900/20">
            <AlertTriangle className="h-10 w-10 text-red-600 dark:text-red-500" />
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground">
            Something went wrong
          </h1>
          <p className="mt-2 text-muted-foreground max-w-md">
            We apologize for the inconvenience. An unexpected error occurred while processing your request.
          </p>
          {this.state.error && (
             <div className="mt-4 p-4 bg-muted/50 rounded-md text-sm font-mono text-left w-full max-w-lg overflow-auto border">
                {this.state.error.toString()}
             </div>
          )}
          <Button onClick={() => window.location.reload()} className="mt-6">
            <RefreshCw className="mr-2 h-4 w-4" />
            Reload Application
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}
