import { AlertCircle, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  description?: string
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorState({
  title = "Something went wrong",
  description = "There was an error loading this content.",
  onRetry,
  retryLabel = "Try again",
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex h-full min-h-[150px] w-full flex-col items-center justify-center space-y-3 rounded-md border border-dashed p-8 text-center animate-in fade-in-50",
        className
      )}
      {...props}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
        <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-500" />
      </div>
      <div className="space-y-1">
        <h3 className="text-lg font-medium text-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          <RotateCcw className="mr-2 h-3 w-3" />
          {retryLabel}
        </Button>
      )}
    </div>
  )
}
