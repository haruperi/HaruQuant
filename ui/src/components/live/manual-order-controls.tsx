"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ShieldBan, Zap } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import LiveTradingAPI from "@/lib/api/live"
import type { PendingOrderType } from "@/types/live"
import { useSettings } from "@/lib/use-settings"
import { defaultTradingPreferences } from "@/lib/trading-defaults"

interface ManualOrderControlsProps {
  sessionId?: number
  defaultSymbol?: string
}

export function ManualOrderControls({ sessionId, defaultSymbol }: ManualOrderControlsProps) {
  const { toast } = useToast()
  const { getJSONField, settings } = useSettings()

  const [volume, setVolume] = useState<string>("0.1")
  const [slPips, setSlPips] = useState<string>("")
  const [tpPips, setTpPips] = useState<string>("")
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [symbol, setSymbol] = useState<string>(defaultSymbol || "XAUUSD")
  const [availableSymbols, setAvailableSymbols] = useState<string[]>(["XAUUSD"])
  const [pendingType, setPendingType] = useState<PendingOrderType>("buy_limit")
  const [pendingPrice, setPendingPrice] = useState<string>("")
  const [lastExecution, setLastExecution] = useState<{
    type: "buy" | "sell"
    symbol: string
    volume: number
    price: number
    orderId: number
    dealId: number
  } | null>(null)

  // Sync with parent symbol selection
  useEffect(() => {
    if (defaultSymbol) {
      setSymbol(defaultSymbol)
    }
  }, [defaultSymbol])

  // Load symbols from settings with defaults fallback
  useEffect(() => {
    // Start with defaults
    let forex = defaultTradingPreferences.forexSymbols.split(",")
    let commodities = defaultTradingPreferences.commoditySymbols.split(",")
    let indices = defaultTradingPreferences.indicesSymbols.split(",")

    if (settings) {
      const prefs = getJSONField("trading_preferences")
      if (prefs) {
        // If user has saved preferences, override defaults where present
        if (prefs.forexSymbols !== undefined) {
            forex = prefs.forexSymbols ? prefs.forexSymbols.split(",") : []
        }
        if (prefs.commoditySymbols !== undefined) {
             commodities = prefs.commoditySymbols ? prefs.commoditySymbols.split(",") : []
        }
        if (prefs.indicesSymbols !== undefined) {
             indices = prefs.indicesSymbols ? prefs.indicesSymbols.split(",") : []
        }
      }
    }

    // Clean and merge
    const cleanList = (list: string[]) => list.map(s => s.trim()).filter(s => s.length > 0)

    const allSymbols = Array.from(new Set([
        ...cleanList(forex),
        ...cleanList(commodities),
        ...cleanList(indices)
    ])).sort()

    if (allSymbols.length > 0) {
        setAvailableSymbols(allSymbols)
        // Set default symbol if current is not in list (and XAUUSD is not in list or priority)
        if (!allSymbols.includes(symbol)) {
            // prefer XAUUSD if available, else first one
            if (allSymbols.includes("XAUUSD")) {
                setSymbol("XAUUSD")
            } else {
                setSymbol(allSymbols[0])
            }
        }
    }
  }, [settings, getJSONField])

  const handleOrder = async (type: "buy" | "sell") => {
    if (!sessionId) {
      toast({
        title: "No Session",
        description: "Please start a trading session first.",
        variant: "destructive",
      })
      return
    }

    if (!volume || parseFloat(volume) <= 0) {
      toast({
        title: "Invalid Volume",
        description: "Please enter a valid volume.",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)
    try {
      const result = await LiveTradingAPI.createManualOrder(sessionId, {
        symbol: symbol,
        volume: parseFloat(volume),
        type: type,
        sl_pips: slPips ? parseFloat(slPips) : undefined,
        tp_pips: tpPips ? parseFloat(tpPips) : undefined,
        comment: "Manual Execution"
      })

      setLastExecution({
        type,
        symbol,
        volume: result.volume,
        price: result.price,
        orderId: result.order_id,
        dealId: result.deal_id,
      })

      const idLabel = result.deal_id ? `Deal #${result.deal_id}` : `Order #${result.order_id}`
      toast({
        title: "Order Placed",
        description: `Placed ${type.toUpperCase()} ${result.volume} lots on ${symbol} at ${result.price} (${idLabel}).`,
      })

      // Reset optional fields
      // setSlPips("")
      // setTpPips("")
    } catch (error: any) {
        console.error("Order failed:", error)
        toast({
            title: "Order Failed",
            description: error.response?.data?.detail || error.message || "Failed to place order",
            variant: "destructive",
        })
    } finally {
        setIsLoading(false)
    }
  }

  const handleFlattenAll = async () => {
    if (!sessionId) {
      toast({
        title: "No Session",
        description: "Please start a trading session first.",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)
    try {
      const result = await LiveTradingAPI.closeAllPositions(sessionId)

      toast({
        title: "Positions Closed",
        description: `Closed ${result.closed_count} position(s) successfully.${result.failed_count > 0 ? ` ${result.failed_count} failed.` : ""}`,
        variant: result.failed_count > 0 ? "destructive" : "default",
      })
    } catch (error: any) {
      console.error("Flatten failed:", error)
      toast({
        title: "Flatten Failed",
        description: error.response?.data?.detail || error.message || "Failed to close positions",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handlePanicStop = async () => {
    if (!sessionId) {
      toast({
        title: "No Session",
        description: "Please start a trading session first.",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)
    try {
      // First close all positions
      const closeResult = await LiveTradingAPI.closeAllPositions(sessionId)

      // Then stop the session
      await LiveTradingAPI.stopSession(sessionId)

      toast({
        title: "Emergency Stop Complete",
        description: `Closed ${closeResult.closed_count} position(s) and stopped the session.`,
      })
    } catch (error: any) {
      console.error("Panic stop failed:", error)
      toast({
        title: "Panic Stop Failed",
        description: error.response?.data?.detail || error.message || "Failed to execute panic stop",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handlePendingOrder = async () => {
    if (!sessionId) {
      toast({
        title: "No Session",
        description: "Please start a trading session first.",
        variant: "destructive",
      })
      return
    }

    if (!volume || parseFloat(volume) <= 0) {
      toast({
        title: "Invalid Volume",
        description: "Please enter a valid volume.",
        variant: "destructive",
      })
      return
    }

    if (!pendingPrice || parseFloat(pendingPrice) <= 0) {
      toast({
        title: "Invalid Price",
        description: "Please enter a valid pending price.",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)
    try {
      await LiveTradingAPI.createPendingOrder(sessionId, {
        symbol: symbol,
        volume: parseFloat(volume),
        type: pendingType,
        price: parseFloat(pendingPrice),
        sl_pips: slPips ? parseFloat(slPips) : undefined,
        tp_pips: tpPips ? parseFloat(tpPips) : undefined,
        comment: "Manual Pending Order",
      })

      toast({
        title: "Pending Order Placed",
        description: `Placed ${pendingType.replace("_", " ").toUpperCase()} for ${symbol}.`,
      })
    } catch (error: any) {
      console.error("Pending order failed:", error)
      toast({
        title: "Order Failed",
        description: error.response?.data?.detail || error.message || "Failed to place pending order",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Quick Execution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="market" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="market">Market</TabsTrigger>
                <TabsTrigger value="pending">Pending</TabsTrigger>
            </TabsList>
            <TabsContent value="market" className="space-y-4 pt-4">
                <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Symbol</Label>
                    <Select value={symbol} onValueChange={setSymbol}>
                        <SelectTrigger>
                            <SelectValue placeholder="Select symbol" />
                        </SelectTrigger>
                        <SelectContent>
                            {availableSymbols.map((sym: string) => (
                                <SelectItem key={sym} value={sym}>
                                    {sym}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">Volume (Lots)</Label>
                    <div className="flex items-center space-x-2">
                        <Input
                            type="number"
                            step="0.01"
                            value={volume}
                            onChange={(e) => setVolume(e.target.value)}
                            className="w-full"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">SL (Pips)</Label>
                        <Input
                            type="number"
                            placeholder="Optional"
                            value={slPips}
                            onChange={(e) => setSlPips(e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground">TP (Pips)</Label>
                        <Input
                            type="number"
                            placeholder="Optional"
                            value={tpPips}
                            onChange={(e) => setTpPips(e.target.value)}
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2">
                    <Button
                        variant="outline"
                        className="text-red-500 hover:text-red-600 border-red-200 hover:bg-red-50 dark:border-red-900/30 dark:hover:bg-red-900/20"
                        onClick={() => handleOrder("sell")}
                        disabled={isLoading}
                    >
                        SELL
                    </Button>
                    <Button
                        variant="outline"
                        className="text-emerald-500 hover:text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:border-emerald-900/30 dark:hover:bg-emerald-900/20"
                        onClick={() => handleOrder("buy")}
                        disabled={isLoading}
                    >
                        BUY
                    </Button>
                </div>
            </TabsContent>
            <TabsContent value="pending" className="pt-4">
                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Order Type</Label>
                        <Select
                          value={pendingType}
                          onValueChange={(value: PendingOrderType) => setPendingType(value)}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="buy_limit">Buy Limit</SelectItem>
                                <SelectItem value="sell_limit">Sell Limit</SelectItem>
                                <SelectItem value="buy_stop">Buy Stop</SelectItem>
                                <SelectItem value="sell_stop">Sell Stop</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label className="text-xs text-muted-foreground">Price</Label>
                        <Input
                          type="number"
                          placeholder="Pending price"
                          value={pendingPrice}
                          onChange={(e) => setPendingPrice(e.target.value)}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">SL (Pips)</Label>
                            <Input
                                type="number"
                                placeholder="Optional"
                                value={slPips}
                                onChange={(e) => setSlPips(e.target.value)}
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">TP (Pips)</Label>
                            <Input
                                type="number"
                                placeholder="Optional"
                                value={tpPips}
                                onChange={(e) => setTpPips(e.target.value)}
                            />
                        </div>
                    </div>

                    <Button
                      className="w-full"
                      onClick={handlePendingOrder}
                      disabled={isLoading}
                    >
                        Place Pending Order
                    </Button>
                </div>
            </TabsContent>
        </Tabs>

        {lastExecution && (
          <div className="rounded-md border border-muted px-3 py-2 text-xs text-muted-foreground">
            Last execution: {lastExecution.type.toUpperCase()} {lastExecution.volume} {lastExecution.symbol} @ {lastExecution.price} (#{lastExecution.dealId || lastExecution.orderId})
          </div>
        )}

        <div className="pt-4 border-t space-y-2">
             <Button
               variant="secondary"
               className="w-full text-xs h-8"
               onClick={handleFlattenAll}
               disabled={isLoading}
             >
                <Zap className="mr-2 h-3 w-3" /> Flatten All Positions
             </Button>
             <Button
               variant="destructive"
               className="w-full text-xs h-8"
               onClick={handlePanicStop}
               disabled={isLoading}
             >
                <ShieldBan className="mr-2 h-3 w-3" /> Panic Close & Stop
             </Button>
        </div>
      </CardContent>
    </Card>
  )
}
