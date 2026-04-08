import { GitPullRequest } from "lucide-react"

import { OperatorPlaceholderPage } from "@/components/operator/operator-placeholder-page"


export default function OperatorProposalsPage() {
  return (
    <OperatorPlaceholderPage
      title="Proposals"
      description="Trade hypothesis and trade proposal contracts now exist, along with proposal-state transitions and repository persistence."
      icon={GitPullRequest}
      readyItems={[
        "Canonical trade hypothesis and proposal contracts are seeded in the schema registry.",
        "Proposal repository methods already exist in the new backend repository layer.",
        "Proposal transition rules are defined for future workflow orchestration.",
      ]}
      nextSlice="Add proposal queue queries, summary cards, and proposal-detail drilldowns."
    />
  )
}
