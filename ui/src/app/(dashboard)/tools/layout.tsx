import { ToolsNav } from "@/components/tools/tools-nav"

export default function ToolsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col h-full w-full">
      <div className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="px-6 pt-6 pb-2">
          <h1 className="text-2xl font-semibold tracking-tight">Tools</h1>
        </div>
        <ToolsNav />
      </div>
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  )
}
