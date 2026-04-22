"use client"

import * as React from "react"

import type { AiChatSemanticBlock } from "@/lib/ai-chat/contracts"

interface SemanticSnapshotScriptProps {
  block: AiChatSemanticBlock
}

export function SemanticSnapshotScript({ block }: SemanticSnapshotScriptProps) {
  const payload = React.useMemo(() => JSON.stringify(block), [block])

  return (
    <script
      type="application/json"
      data-ai-chat-semantic-block={block.blockType}
      dangerouslySetInnerHTML={{ __html: payload }}
    />
  )
}
