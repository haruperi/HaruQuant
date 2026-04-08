import { OperatorShell } from "@/components/operator/operator-shell"


export default function OperatorLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <OperatorShell>{children}</OperatorShell>
}
