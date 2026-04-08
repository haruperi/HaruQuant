import { ArrowRight, type LucideIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"


interface OperatorPlaceholderPageProps {
  title: string
  description: string
  icon: LucideIcon
  readyItems: string[]
  nextSlice: string
}


export function OperatorPlaceholderPage({
  title,
  description,
  icon: Icon,
  readyItems,
  nextSlice,
}: OperatorPlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <Card className="border-slate-200/70 shadow-sm">
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div className="space-y-2">
            <Badge variant="outline" className="border-slate-300 text-slate-700">
              Placeholder
            </Badge>
            <div>
              <CardTitle className="text-2xl">{title}</CardTitle>
              <CardDescription className="mt-2 max-w-2xl">{description}</CardDescription>
            </div>
          </div>
          <Icon className="h-6 w-6 text-slate-500" />
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Ready Now</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              {readyItems.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <ArrowRight className="mt-0.5 h-4 w-4 text-slate-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-dashed bg-background p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Next Slice</p>
            <p className="mt-3 text-sm text-slate-700">{nextSlice}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
