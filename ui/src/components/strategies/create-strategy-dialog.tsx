"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, Loader2 } from "lucide-react"
import { useStrategies, useStrategyMutations } from "@/lib/use-strategies"
import { strategyApi } from "@/lib/api/strategies"
import { toast } from "sonner"
import { useRouter } from "next/navigation"

interface CreateStrategyDialogProps {
  onSuccess?: () => void
}

const EMPTY_STRATEGY_CODE = `from apps.strategy import Strategy
from apps.indicator import sma, ema, rsi

class MyStrategy(Strategy):
    """
    Custom trading strategy.

    Example: Simple MA Crossover
    """

    def setup_indicators(self):
        """Calculate indicators before backtest starts."""
        # Access parameters from Settings panel
        fast_period = self.params.get('fast_period', 20)
        slow_period = self.params.get('slow_period', 50)

        # Calculate indicators - they create columns: sma_{window}, ema_{window}, rsi_{window}
        self.data = sma(self.data, window=fast_period, price_col='Close')
        self.data = sma(self.data, window=slow_period, price_col='Close')

    def next(self):
        """Execute on each new bar."""
        # Get current indicator values
        fast_period = self.params.get('fast_period', 20)
        slow_period = self.params.get('slow_period', 50)

        sma_fast = self.current(f'sma_{fast_period}')
        sma_slow = self.current(f'sma_{slow_period}')

        # Trading logic
        if sma_fast > sma_slow and self.position.is_flat:
            self.buy()
        elif sma_fast < sma_slow and self.position.is_long:
            self.sell()
`

export function CreateStrategyDialog({ onSuccess }: CreateStrategyDialogProps) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [templateId, setTemplateId] = useState<string>("empty")
  const [templateCode, setTemplateCode] = useState("")

  const { strategies, loading: loadingStrategies } = useStrategies()
  const { createStrategy, loading: creating } = useStrategyMutations()

  // Fetch template code when template is selected
  useEffect(() => {
    const fetchTemplateCode = async () => {
      // If it's the "empty" template, fetch from API
      if (templateId === "empty") {
        try {
          const templateData = await strategyApi.getTemplate("empty")
          setTemplateCode(templateData.code)
          return
        } catch (error) {
          console.error("Failed to fetch empty template:", error)
          toast.error("Failed to load empty template")
          // Fallback to hardcoded template if API fails
          setTemplateCode(EMPTY_STRATEGY_CODE)
          return
        }
      }

      // Otherwise, it's an existing strategy being used as template
      try {
        const strategyId = parseInt(templateId)
        const strategy = strategies.find(s => s.id === strategyId)

        if (strategy?.active_version_id) {
          const codeData = await strategyApi.getVersionCode(strategyId, strategy.active_version_id)
          setTemplateCode(codeData.code)
        }
      } catch (error) {
        console.error("Failed to fetch template code:", error)
        toast.error("Failed to load template code")
        setTemplateCode(EMPTY_STRATEGY_CODE)
      }
    }

    if (open) {
      fetchTemplateCode()
    }
  }, [templateId, strategies, open])

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Please enter a strategy name")
      return
    }

    // Sanitize code to remove any global indentation
    const sanitizeCode = (code: string): string => {
      const lines = code.split('\n')

      // Find minimum indentation (excluding empty lines)
      let minIndent = Infinity
      for (const line of lines) {
        if (line.trim().length > 0) {
          const leadingSpaces = line.match(/^\s*/)?.[0].length || 0
          minIndent = Math.min(minIndent, leadingSpaces)
        }
      }

      // Remove the minimum indentation from all lines
      if (minIndent > 0 && minIndent !== Infinity) {
        return lines.map(line => {
          if (line.trim().length === 0) return ''
          return line.substring(minIndent)
        }).join('\n')
      }

      return code
    }

    try {
      const codeToSave = sanitizeCode(templateCode || EMPTY_STRATEGY_CODE)

      const result = await createStrategy({
        name: name.trim(),
        description: description.trim() || undefined,
        code: codeToSave,
        parameters: {},
      })

      toast.success("Strategy created successfully!")
      setOpen(false)

      // Reset form
      setName("")
      setDescription("")
      setTemplateId("empty")

      // Call success callback if provided
      if (onSuccess) {
        onSuccess()
      }

      // Navigate to the editor
      router.push(`/strategies/${result.id}`)
    } catch (error) {
      // Error is already handled by the mutation hook
      console.error("Failed to create strategy:", error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Strategy
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Strategy</DialogTitle>
          <DialogDescription>
            Initialize a new trading algorithm. You can configure parameters later.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              placeholder="My Alpha Strategy"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="template">Template</Label>
            <Select value={templateId} onValueChange={setTemplateId} disabled={loadingStrategies}>
              <SelectTrigger id="template">
                <SelectValue placeholder="Select a template..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="empty">Empty Strategy</SelectItem>
                {strategies.map((strategy) => (
                  <SelectItem key={strategy.id} value={strategy.id.toString()}>
                    {strategy.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="desc">Description</Label>
            <Textarea
              id="desc"
              placeholder="Brief description of your strategy..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} disabled={creating || !name.trim()}>
            {creating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Strategy"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
