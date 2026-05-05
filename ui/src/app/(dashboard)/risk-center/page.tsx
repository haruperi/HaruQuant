import { AgenticFirmPage } from "@/components/agentic-firm/agentic-firm-page"

export default function RiskCenterPage() {
  return (
    <AgenticFirmPage
      title="Risk Center"
      subtitle="Portfolio exposure, VaR/CVaR, correlations, RiskGovernor blocks, approvals, and kill-switch state."
      status="Hard gates"
      sections={[
        { title: "Exposure", items: ["Portfolio exposure", "VaR/CVaR", "Correlation matrix"] },
        { title: "Controls", items: ["RiskGovernor blocks", "Risk approvals", "Kill-switch status"] },
      ]}
    />
  )
}
