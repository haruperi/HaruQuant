import { ShieldCheck } from "lucide-react"

import { OperatorPlaceholderPage } from "@/components/operator/operator-placeholder-page"


export default function OperatorApprovalsPage() {
  return (
    <OperatorPlaceholderPage
      title="Approvals"
      description="Approval requests, distinct-voter rules, and override-request validation are already scaffolded on the backend."
      icon={ShieldCheck}
      readyItems={[
        "Approval domain state machine is defined.",
        "Approval request creation and distinct reviewer voting rules are implemented.",
        "Override request skeleton validation is available.",
      ]}
      nextSlice="Connect approval queues and decision actions to the operator API once command endpoints are introduced."
    />
  )
}
