import { AgenticFirmPage } from "@/components/agentic-firm/agentic-firm-page"

export default function StrategyLabPage() {
  return (
    <AgenticFirmPage
      title="Strategy Lab"
      subtitle="Strategy ideas, specs, generated code versions, formal reviews, and lifecycle state in one operator workspace."
      status="Evidence first"
      sections={[
        { title: "Research", items: ["Strategy ideas", "Strategy specs", "Lifecycle status"] },
        { title: "Review", items: ["Strategy code versions", "Strategy reviews", "Rejected and retired paths"] },
      ]}
    />
  )
}
