import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { OperatorAuthorityBadge } from "./operator-authority-badge"
import { operatorReplayBundles } from "./operator-mock-data"


export function OperatorReplayView() {
  const replay = operatorReplayBundles[0]

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Replay bundle</CardTitle>
          <CardDescription>Deterministic reconstruction package for one supervised workflow.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Bundle ID</p>
              <p className="mt-2 font-medium">{replay.replayBundleId}</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Completeness</p>
              <p className="mt-2 font-medium">{replay.completeness}</p>
            </div>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Manifest Hash</p>
            <p className="mt-2 font-mono text-sm">{replay.manifestHash}</p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Object Store URI</p>
            <p className="mt-2 text-sm text-slate-700">{replay.objectStoreUri}</p>
            <div className="mt-3">
              <OperatorAuthorityBadge authorityState={replay.authorityState} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Included refs</CardTitle>
          <CardDescription>Artifacts that would be pulled into the audit export and replay reconstruction.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Badge variant="outline" className="border-slate-300 text-slate-700">
            {replay.exportProfile}
          </Badge>
          <div className="flex flex-wrap gap-2">
            {replay.includedRefs.map((ref) => (
              <Badge key={ref} variant="secondary">
                {ref}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
