import { CurrencyStrengthDashboard } from "@/components/dashboard/currency-strength-dashboard"

export default function CurrencyStrengthPage() {
  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <CurrencyStrengthDashboard autoRefresh={true} />
    </div>
  )
}
