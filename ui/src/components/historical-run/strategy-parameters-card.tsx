"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"

interface StrategyParametersCardProps {
  values: Record<string, unknown>
  parameterTypes?: Record<string, string>
  onChange: (key: string, value: unknown) => void
  loading?: boolean
}

function inferType(value: unknown, explicitType?: string): string {
  if (explicitType) return explicitType
  if (typeof value === "boolean") return "boolean"
  if (typeof value === "number") return Number.isInteger(value) ? "int" : "float"
  return "string"
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return ""
  if (typeof value === "object") {
    try {
      return JSON.stringify(value)
    } catch {
      return ""
    }
  }
  return String(value)
}

export function coerceStrategyParameterValue(raw: string | boolean, type: string): unknown {
  switch (type) {
    case "boolean":
      return Boolean(raw)
    case "int":
    case "integer":
      return Number.parseInt(String(raw), 10) || 0
    case "float":
    case "number":
      return Number.parseFloat(String(raw)) || 0
    case "json":
    case "dict":
    case "object":
    case "list":
    case "array":
      try {
        return JSON.parse(String(raw))
      } catch {
        return String(raw)
      }
    default:
      return String(raw)
  }
}

export function StrategyParametersCard({
  values,
  parameterTypes,
  onChange,
  loading = false,
}: StrategyParametersCardProps) {
  const keys = Object.keys(values)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Strategy Parameters</CardTitle>
        <CardDescription>
          {loading
            ? "Loading active-version parameters..."
            : keys.length > 0
              ? "Override the strategy parameters used for this run."
              : "No declared parameters were found for the selected strategy."}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {loading ? (
          <div className="text-sm text-muted-foreground">Loading strategy parameters...</div>
        ) : keys.length === 0 ? (
          <div className="text-sm text-muted-foreground">This strategy exposes no editable parameters.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {keys.map((key) => {
              const value = values[key]
              const type = inferType(value, parameterTypes?.[key])
              return (
                <div key={key} className="space-y-2">
                  <Label htmlFor={`strategy-param-${key}`}>{key}</Label>
                  {type === "boolean" ? (
                    <div className="flex h-10 items-center rounded-md border px-3">
                      <Switch
                        id={`strategy-param-${key}`}
                        checked={Boolean(value)}
                        onCheckedChange={(checked) => onChange(key, checked)}
                      />
                      <span className="ml-3 text-sm text-muted-foreground">
                        {Boolean(value) ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                  ) : (
                    <Input
                      id={`strategy-param-${key}`}
                      value={displayValue(value)}
                      onChange={(event) =>
                        onChange(
                          key,
                          coerceStrategyParameterValue(event.target.value, type)
                        )
                      }
                    />
                  )}
                  <div className="text-xs text-muted-foreground">Type: {type}</div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
