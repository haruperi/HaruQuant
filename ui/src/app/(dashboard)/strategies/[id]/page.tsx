import { EditorLayout } from "@/components/strategies/editor/editor-layout"
import { use } from "react"

export default function StrategyEditorPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params)
    return <EditorLayout strategyId={id} />
}
