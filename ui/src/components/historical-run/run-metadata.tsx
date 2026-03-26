"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

interface RunMetadataProps {
  values: {
    alias: string
    description: string
  }
  onChange: (key: string, value: string) => void
}

export function RunMetadata({ values, onChange }: RunMetadataProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Metadata</CardTitle>
        <CardDescription>Optional details to identify this run.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <div className="space-y-2">
          <Label htmlFor="alias">Alias</Label>
          <Input
            id="alias"
            placeholder="e.g. Trend Following V1 - EURUSD H1"
            value={values.alias}
            onChange={(e) => onChange("alias", e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            placeholder="Describe the hypothesis or changes being tested..."
            className="min-h-[100px]"
            value={values.description}
            onChange={(e) => onChange("description", e.target.value)}
          />
        </div>
      </CardContent>
    </Card>
  )
}
