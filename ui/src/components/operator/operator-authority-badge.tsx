import { Badge } from "@/components/ui/badge"


const authorityStateClassNames: Record<string, string> = {
  AUTHORITATIVE: "border-emerald-300 text-emerald-700",
  PROVISIONAL: "border-amber-300 text-amber-700",
  RECONCILING: "border-rose-300 text-rose-700",
}


export function OperatorAuthorityBadge({ authorityState }: { authorityState: string }) {
  return (
    <Badge
      variant="outline"
      className={authorityStateClassNames[authorityState] ?? "border-slate-300 text-slate-700"}
    >
      {authorityState}
    </Badge>
  )
}
