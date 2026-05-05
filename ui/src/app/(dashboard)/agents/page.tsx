import { AgenticFirmPage } from "@/components/agentic-firm/agentic-firm-page"

export default function AgentsPage() {
  return (
    <AgenticFirmPage
      title="Agent Task Board"
      subtitle="A scan-first view of departments, ownership, task state, dependencies, failures, blocks, and cost usage."
      status="Control plane"
      sections={[
        { title: "Agents", items: ["All agents", "Task status", "Task dependencies"] },
        { title: "Operations", items: ["Running jobs", "Failed tasks", "Blocked tasks", "Cost usage"] },
      ]}
    />
  )
}
