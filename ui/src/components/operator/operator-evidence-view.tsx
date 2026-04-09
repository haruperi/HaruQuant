import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { operatorEvidenceBundles } from "./operator-mock-data"


export function OperatorEvidenceView() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Evidence bundles</CardTitle>
          <CardDescription>
            Review lifecycle evidence packages before promotion and governance actions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {operatorEvidenceBundles.map((bundle) => (
            <div key={bundle.evidenceBundleId} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900">{bundle.evidenceBundleId}</p>
                  <p className="text-sm text-muted-foreground">{bundle.strategyId}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">{bundle.lifecycleState}</Badge>
                  <Badge variant="outline" className="border-slate-300 text-slate-700">
                    {bundle.bundleType}
                  </Badge>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Hash</p>
                  <p className="mt-1 text-sm text-slate-700">{bundle.contentHash}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Storage</p>
                  <p className="mt-1 text-sm text-slate-700">{bundle.contentRef}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Artifacts</p>
                  <p className="mt-1 text-sm text-slate-700">{bundle.artifactCount}</p>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader>
          <CardTitle>Bundle contents</CardTitle>
          <CardDescription>
            Inspect the artifact mix that backs each promotion and audit decision.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {operatorEvidenceBundles.map((bundle) => (
            <div key={bundle.evidenceBundleId} className="rounded-lg border p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-slate-900">{bundle.evidenceBundleId}</p>
                <Badge variant="outline" className="border-emerald-300 text-emerald-700">
                  {bundle.freshnessStatus}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {bundle.artifacts.map((artifact) => (
                  <Badge key={artifact} variant="secondary">
                    {artifact}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
