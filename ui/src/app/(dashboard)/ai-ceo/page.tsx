import { AgenticFirmPage } from "@/components/agentic-firm/agentic-firm-page"

export default function AiCeoPage() {
  return (
    <AgenticFirmPage
      title="AI CEO"
      subtitle="The operator-facing control room for planner output, active work, evidence, final memos, and approval requests."
      status="Governed interface"
      sections={[
        { title: "CEO Chat", items: ["Chat with CEO Agent", "Planner output visible", "Final memo visible"] },
        { title: "Active Work", items: ["Active task tree", "Evidence references", "Approval requests"] },
      ]}
    />
  )
}
