import { Search } from "lucide-react"

import { OperatorPlaceholderPage } from "@/components/operator/operator-placeholder-page"


export default function OperatorReplayPage() {
  return (
    <OperatorPlaceholderPage
      title="Replay"
      description="Replay bundle contracts and audit/research repository scaffolding are in place for later deterministic replay tooling."
      icon={Search}
      readyItems={[
        "Replay bundle contracts are implemented and seeded.",
        "Audit and research repositories already exist in the backend.",
        "Workflow history tables provide the baseline event trail.",
      ]}
      nextSlice="Attach replay bundle listing, export metadata, and integrity views once replay services are added."
    />
  )
}
