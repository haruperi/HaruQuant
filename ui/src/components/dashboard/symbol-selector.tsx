"use client"

import * as React from "react"
import { Search, ChevronDown, Check } from "lucide-react"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { edgeLabApi } from "@/lib/api/edge"
import { Loader2 } from "lucide-react"

interface Instrument {
  symbol: string
  name: string
  category: string
  subCategory?: string
}

interface SymbolSelectorProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (symbol: string) => void
  currentSymbol?: string
}

export function SymbolSelector({
  open,
  onOpenChange,
  onSelect,
  currentSymbol,
}: SymbolSelectorProps) {
  const [search, setSearch] = React.useState("")
  const [category, setCategory] = React.useState("All")
  const [instruments, setInstruments] = React.useState<Instrument[]>([])
  const [categories, setCategories] = React.useState<string[]>(["All"])
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    const fetchSymbols = async () => {
      setLoading(true)
      try {
        const data = await edgeLabApi.getSymbols()
        setInstruments(data)
        const cats = ["All", ...Array.from(new Set(data.map((i: Instrument) => i.category)))]
        setCategories(cats)
      } catch (error) {
        console.error("Failed to fetch symbols", error)
      } finally {
        setLoading(false)
      }
    }

    if (open) {
      void fetchSymbols()
    }
  }, [open])

  const filteredInstruments = instruments.filter((item) => {
    const matchesSearch =
      item.symbol.toLowerCase().includes(search.toLowerCase()) ||
      item.name.toLowerCase().includes(search.toLowerCase())
    const matchesCategory = category === "All" || item.category === category
    return matchesSearch && matchesCategory
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl border-slate-800 bg-[#0c121e] p-0 text-slate-100 shadow-2xl overflow-hidden rounded-[24px]">
        <DialogTitle className="sr-only">Select Symbol</DialogTitle>

        <div className="flex flex-col h-[600px]">
          {/* Search Header */}
          <div className="p-4 pb-2">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search for CFD instruments..."
                className="h-12 w-full rounded-full border-none bg-slate-800/50 pl-11 text-base placeholder:text-slate-500 focus-visible:ring-1 focus-visible:ring-slate-700"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
              />
            </div>
          </div>

          {/* Categories Tabs */}
          <div className="px-4 py-2 overflow-x-auto no-scrollbar">
            <Tabs value={category} onValueChange={setCategory} className="w-full">
              <TabsList className="h-auto w-full justify-start gap-2 bg-transparent p-0 flex-nowrap">
                {categories.map((cat) => (
                  <TabsTrigger
                    key={cat}
                    value={cat}
                    className={cn(
                      "rounded-lg border border-slate-700/50 bg-slate-800/30 px-4 py-1.5 text-xs font-medium text-slate-400 transition-all flex-shrink-0",
                      "data-[state=active]:border-indigo-500/50 data-[state=active]:bg-indigo-500/20 data-[state=active]:text-indigo-400"
                    )}
                  >
                    {category === cat && category !== "All" && (
                      <Check className="mr-1.5 h-3 w-3 inline-block" />
                    )}
                    {cat}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          {/* Instruments List */}
          <ScrollArea className="flex-1 px-2 mt-2">
            <div className="grid gap-1 p-2">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-20 text-slate-400">
                  <Loader2 className="mb-3 h-8 w-8 animate-spin opacity-50" />
                  <p className="text-sm font-medium">Fetching symbols from MT5...</p>
                </div>
              ) : (
                <>
                  {filteredInstruments.map((item) => (
                    <button
                      key={item.symbol}
                      onClick={() => {
                        onSelect(item.symbol)
                        onOpenChange(false)
                      }}
                      className={cn(
                        "flex items-center justify-between rounded-xl px-4 py-3.5 text-left transition-all hover:bg-slate-800/40 group",
                        currentSymbol === item.symbol && "bg-slate-800/60"
                      )}
                    >
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[15px] font-bold tracking-tight text-slate-100">
                          {item.symbol}
                        </span>
                        <span className="text-xs font-medium text-slate-400 group-hover:text-slate-300">
                          {item.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold bg-slate-800/50 px-2 py-0.5 rounded">
                          {item.category}
                        </span>
                        {currentSymbol === item.symbol && (
                          <div className="rounded-full bg-indigo-500/20 p-1">
                            <Check className="h-4 w-4 text-indigo-400" />
                          </div>
                        )}
                      </div>
                    </button>
                  ))}

                  {filteredInstruments.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-20 text-slate-500">
                      <Search className="mb-3 h-10 w-10 opacity-20" />
                      <p>No instruments found</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}
