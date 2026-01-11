"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertTriangle, TrendingUp, BarChart3, List, PieChart, Save, Loader2 } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { useSettings } from "@/lib/use-settings"
import { useState, useEffect } from "react"
import { toast } from "sonner"

interface TradingPreferences {
  riskManagementActive: boolean
  activeBrokerAccount: string
  magicNumber: string
  maxDeviation: string
  maxSlippage: string
  maxSpread: string
  leverage: string
  initialCapital: string
  defaultLotSize: string
  riskPerTrade: string
  riskThreshold: string
  correlationPeriod: string
  adrPeriod: string
  volatilityPeriod: string
  confidenceLevel: string
  chartBackground: string
  bullishCandle: string
  bearishCandle: string
  forexSymbols: string
  commoditySymbols: string
  indicesSymbols: string
  maxDailyLoss: string
  maxDrawdown: string
  maxExposure: string
  maxPositionSize: string
  maxPositions: string
  minMarginLevel: string
  autoKillDailyLoss: boolean
  autoKillDrawdown: boolean
}

const defaultPreferences: TradingPreferences = {
  riskManagementActive: true,
  activeBrokerAccount: "",
  magicNumber: "123456",
  maxDeviation: "5",
  maxSlippage: "3",
  maxSpread: "10",
  leverage: "400",
  initialCapital: "10000",
  defaultLotSize: "0.1",
  riskPerTrade: "1",
  riskThreshold: "10",
  correlationPeriod: "10",
  adrPeriod: "10",
  volatilityPeriod: "5",
  confidenceLevel: "0.95",
  chartBackground: "#161A25",
  bullishCandle: "#26A69A",
  bearishCandle: "#EF5350",
  forexSymbols: "AUDCAD,AUDCHF,AUDJPY,AUDNZD,AUDUSD,CADCHF,CADJPY,CHFJPY,EURAUD,EURCAD,EURCHF,EURGBP,EURJPY,EURNZD,EURUSD,GBPAUD,GBPCAD,GBPCHF,GBPJPY,GBPNZD,GBPUSD,NZDCAD,NZDCHF,NZDJPY,NZDUSD,USDCHF,USDCAD,USDJPY",
  commoditySymbols: "XAUUSD,XAUEUR,XAUGBP,XAUJPY,XAUAUD,XAUCHF,XAGUSD",
  indicesSymbols: "US500,US30,UK100,GER40,NAS100,USDX,EURX",
  maxDailyLoss: "5000",
  maxDrawdown: "10",
  maxExposure: "100000",
  maxPositionSize: "1",
  maxPositions: "10",
  minMarginLevel: "100",
  autoKillDailyLoss: false,
  autoKillDrawdown: false,
}

export function TradingSettings() {
  const { settings, isLoading, updateJSONField } = useSettings()
  const [preferences, setPreferences] = useState<TradingPreferences>(defaultPreferences)
  const [brokerAccounts, setBrokerAccounts] = useState<Array<{ id: string; name: string; environment: string }>>([])
  const [isSaving, setIsSaving] = useState(false)

  // Load trading preferences from settings
  useEffect(() => {
    if (settings) {
      try {
        let tradingPrefs;
        if (typeof settings.trading_preferences === 'string') {
          tradingPrefs = JSON.parse(settings.trading_preferences || "{}")
        } else {
          tradingPrefs = settings.trading_preferences || {}
        }
        setPreferences({ ...defaultPreferences, ...tradingPrefs })

        // Load broker accounts
        let brokerCreds;
        if (typeof settings.broker_credentials === 'string') {
          brokerCreds = JSON.parse(settings.broker_credentials || "{}")
        } else {
          brokerCreds = settings.broker_credentials || {}
        }
        const accounts = brokerCreds.accounts || []
        setBrokerAccounts(accounts)
      } catch (e) {
        setPreferences(defaultPreferences)
      }
    }
  }, [settings])

  const updatePreference = (key: keyof TradingPreferences, value: any) => {
    setPreferences(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await updateJSONField("trading_preferences", preferences)
    } catch (error) {
      // Error already handled by updateJSONField
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* 1. Global Risk Engine (Red Card) */}
      <Card className="border-red-500/20 bg-red-500/5">
        <CardHeader className="pb-3">
          <div className="flex items-center space-x-2 text-red-500">
            <AlertTriangle className="h-5 w-5" />
            <CardTitle>Global Risk Engine</CardTitle>
          </div>
          <CardDescription>
            Master switch for risk management enforcement.
          </CardDescription>
        </CardHeader>
        <CardContent>
            <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <Label className="text-base font-medium">Risk Management Active</Label>
                    <p className="text-sm text-muted-foreground">Disabling this allows strategies to bypass all limits.</p>
                </div>
                <Switch
                  checked={preferences.riskManagementActive}
                  onCheckedChange={(checked) => updatePreference("riskManagementActive", checked)}
                  aria-label="Risk Switch"
                />
            </div>
        </CardContent>
      </Card>

      {/* 2. Execution & Strategy Defaults */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            <CardTitle>Execution & Strategy Defaults</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
             <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Active Broker Account</Label>
                    <Select
                      value={preferences.activeBrokerAccount}
                      onValueChange={(value) => updatePreference("activeBrokerAccount", value)}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder="Select account" />
                        </SelectTrigger>
                        <SelectContent>
                            {brokerAccounts.length === 0 ? (
                              <SelectItem value="none" disabled>No broker accounts configured</SelectItem>
                            ) : (
                              brokerAccounts.map((account) => (
                                <SelectItem key={account.id} value={account.id}>
                                  {account.name} ({account.environment})
                                </SelectItem>
                              ))
                            )}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-2">
                    <Label>Magic Number (EA ID)</Label>
                    <Input
                      value={preferences.magicNumber}
                      onChange={(e) => updatePreference("magicNumber", e.target.value)}
                    />
                </div>
             </div>

             <div className="grid grid-cols-4 gap-4">
                 <div className="space-y-2">
                    <Label>Max Deviation (pts)</Label>
                    <Input
                      type="number"
                      value={preferences.maxDeviation}
                      onChange={(e) => updatePreference("maxDeviation", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Slippage (pts)</Label>
                    <Input
                      type="number"
                      value={preferences.maxSlippage}
                      onChange={(e) => updatePreference("maxSlippage", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Spread (pips)</Label>
                    <Input
                      type="number"
                      value={preferences.maxSpread}
                      onChange={(e) => updatePreference("maxSpread", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Leverage</Label>
                    <Input
                      type="number"
                      value={preferences.leverage}
                      onChange={(e) => updatePreference("leverage", e.target.value)}
                    />
                </div>
             </div>

             <div className="grid grid-cols-4 gap-4">
                 <div className="space-y-2">
                    <Label>Initial Capital ($)</Label>
                    <Input
                      type="number"
                      value={preferences.initialCapital}
                      onChange={(e) => updatePreference("initialCapital", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Default Lot Size</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={preferences.defaultLotSize}
                      onChange={(e) => updatePreference("defaultLotSize", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Risk Per Trade (%)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={preferences.riskPerTrade}
                      onChange={(e) => updatePreference("riskPerTrade", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Risk Threshold (%)</Label>
                    <Input
                      type="number"
                      value={preferences.riskThreshold}
                      onChange={(e) => updatePreference("riskThreshold", e.target.value)}
                    />
                </div>
             </div>
        </CardContent>
      </Card>

      {/* 3. Market Analysis */}
      <Card>
        <CardHeader>
           <div className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <CardTitle>Market Analysis</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
            <div className="grid grid-cols-4 gap-4">
                 <div className="space-y-2">
                    <Label>Correlation Period</Label>
                    <Input
                      type="number"
                      value={preferences.correlationPeriod}
                      onChange={(e) => updatePreference("correlationPeriod", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>ADR Period</Label>
                    <Input
                      type="number"
                      value={preferences.adrPeriod}
                      onChange={(e) => updatePreference("adrPeriod", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Volatility Period</Label>
                    <Input
                      type="number"
                      value={preferences.volatilityPeriod}
                      onChange={(e) => updatePreference("volatilityPeriod", e.target.value)}
                    />
                </div>
                 <div className="space-y-2">
                    <Label>Confidence Level (0-1)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      value={preferences.confidenceLevel}
                      onChange={(e) => updatePreference("confidenceLevel", e.target.value)}
                    />
                </div>
            </div>
        </CardContent>
      </Card>

      {/* 4. Chart Visuals */}
      <Card>
        <CardHeader>
           <div className="flex items-center space-x-2">
            <PieChart className="h-5 w-5 text-primary" />
            <CardTitle>Chart Visuals</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
            <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                    <Label>Chart Background</Label>
                    <div className="flex gap-2">
                        <div className="h-10 w-10 rounded border" style={{ backgroundColor: preferences.chartBackground }}></div>
                        <Input
                          type="color"
                          value={preferences.chartBackground}
                          onChange={(e) => updatePreference("chartBackground", e.target.value)}
                          className="w-full"
                        />
                    </div>
                </div>
                <div className="space-y-2">
                    <Label>Bullish Candle</Label>
                    <div className="flex gap-2">
                        <div className="h-10 w-10 rounded border" style={{ backgroundColor: preferences.bullishCandle }}></div>
                        <Input
                          type="color"
                          value={preferences.bullishCandle}
                          onChange={(e) => updatePreference("bullishCandle", e.target.value)}
                          className="w-full"
                        />
                    </div>
                </div>
                 <div className="space-y-2">
                    <Label>Bearish Candle</Label>
                    <div className="flex gap-2">
                        <div className="h-10 w-10 rounded border" style={{ backgroundColor: preferences.bearishCandle }}></div>
                        <Input
                          type="color"
                          value={preferences.bearishCandle}
                          onChange={(e) => updatePreference("bearishCandle", e.target.value)}
                          className="w-full"
                        />
                    </div>
                </div>
            </div>
        </CardContent>
      </Card>

       {/* 5. Symbol Lists */}
      <Card>
        <CardHeader>
           <div className="flex items-center space-x-2">
            <List className="h-5 w-5 text-primary" />
            <CardTitle>Symbol Lists</CardTitle>
          </div>
          <CardDescription>
            Comma-separated lists of symbols to trade.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="space-y-2">
                <Label>Forex Symbols</Label>
                <Textarea
                  className="min-h-[60px]"
                  value={preferences.forexSymbols}
                  onChange={(e) => updatePreference("forexSymbols", e.target.value)}
                />
            </div>
             <div className="space-y-2">
                <Label>Commodity Symbols</Label>
                <Textarea
                  className="min-h-[60px]"
                  value={preferences.commoditySymbols}
                  onChange={(e) => updatePreference("commoditySymbols", e.target.value)}
                />
            </div>
             <div className="space-y-2">
                <Label>Indices Symbols</Label>
                <Textarea
                  className="min-h-[60px]"
                  value={preferences.indicesSymbols}
                  onChange={(e) => updatePreference("indicesSymbols", e.target.value)}
                />
            </div>
        </CardContent>
      </Card>

       {/* 6. Global Risk Limits */}
      <Card>
         <CardHeader>
          <CardTitle>Global Risk Limits</CardTitle>
          <CardDescription>
            Hard limits enforced by the risk management engine.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <Label>Max Daily Loss ($)</Label>
                    <Input
                      type="number"
                      value={preferences.maxDailyLoss}
                      onChange={(e) => updatePreference("maxDailyLoss", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Drawdown (%)</Label>
                    <Input
                      type="number"
                      value={preferences.maxDrawdown}
                      onChange={(e) => updatePreference("maxDrawdown", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Exposure ($)</Label>
                    <Input
                      type="number"
                      value={preferences.maxExposure}
                      onChange={(e) => updatePreference("maxExposure", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Position Size (Lots)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={preferences.maxPositionSize}
                      onChange={(e) => updatePreference("maxPositionSize", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Max Positions (Count)</Label>
                    <Input
                      type="number"
                      value={preferences.maxPositions}
                      onChange={(e) => updatePreference("maxPositions", e.target.value)}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Min Margin Level (%)</Label>
                    <Input
                      type="number"
                      value={preferences.minMarginLevel}
                      onChange={(e) => updatePreference("minMarginLevel", e.target.value)}
                    />
                </div>
            </div>

            <div className="flex items-center justify-between pt-2">
                <Label>Auto-Kill on Daily Loss Limit</Label>
                <Switch
                  checked={preferences.autoKillDailyLoss}
                  onCheckedChange={(checked) => updatePreference("autoKillDailyLoss", checked)}
                />
            </div>
            <div className="flex items-center justify-between">
                <Label>Auto-Kill on Drawdown Limit</Label>
                <Switch
                  checked={preferences.autoKillDrawdown}
                  onCheckedChange={(checked) => updatePreference("autoKillDrawdown", checked)}
                />
            </div>
        </CardContent>
         <CardFooter className="border-t px-6 py-4">
             <Button onClick={handleSave} disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save All Trading Settings
                  </>
                )}
             </Button>
        </CardFooter>
      </Card>

    </div>
  )
}
