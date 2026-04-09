"use client"

import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"


type OperatorEvent = {
  type: string
  message: string
}


export function OperatorLiveEvents() {
  const [events, setEvents] = useState<OperatorEvent[]>([])

  useEffect(() => {
    const stream = new EventSource("/api/operator/events/stream")
    stream.onmessage = (event) => {
      const nextEvent = JSON.parse(event.data) as OperatorEvent
      setEvents((current) => [nextEvent, ...current].slice(0, 6))
    }
    return () => {
      stream.close()
    }
  }, [])

  return (
    <Card className="border-slate-200/70 shadow-sm">
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>Live event stream</CardTitle>
            <CardDescription>Recent operator-plane workflow, approval, and incident events.</CardDescription>
          </div>
          <Badge variant="outline" className="border-emerald-300 text-emerald-700">
            SSE
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">Waiting for operator events...</p>
        ) : (
          events.map((event, index) => (
            <div key={`${event.type}-${index}`} className="rounded-lg border p-3 text-sm">
              <p className="font-medium text-slate-900">{event.type}</p>
              <p className="mt-1 text-slate-700">{event.message}</p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}
