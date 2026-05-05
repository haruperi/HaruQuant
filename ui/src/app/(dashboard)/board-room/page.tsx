import { AgenticFirmPage } from "@/components/agentic-firm/agentic-firm-page"

export default function BoardRoomPage() {
  return (
    <AgenticFirmPage
      title="Board Room"
      subtitle="Weekly reports, approval queue, live activation requests, allocation requests, promotions, and incidents."
      status="Human approval"
      sections={[
        { title: "Reports", items: ["Weekly reports", "Incident reports", "Strategy promotion requests"] },
        { title: "Approvals", items: ["Approval queue", "Live activation requests", "Allocation requests"] },
      ]}
    />
  )
}
