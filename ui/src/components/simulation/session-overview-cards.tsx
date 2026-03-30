"use client"

import { Activity, PlayCircle, ShieldAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface SessionOverviewCardsProps {
  sessionDetails: {
    sessionNumber: string
    sessionName: string
    step: string
    login: string
    server: string
    leverage: string
    commission: string
    slippageType: string
    spreadType: string
    dataResolution: string
  }
  strategyControl: {
    strategyLabel: string
    symbols: string
    timeframe: string
    approvedCount: string
    rejectedCount: string
  }
  riskMonitor: {
    varCap: { current: string; limit: string; progress: number }
    cvarCap: { current: string; limit: string; progress: number }
    currentDrawdown: string
    maxDrawdown: string
    drawdownVelocity: string
    timeUnderWater: string
    scores: Array<{
      key: string
      label: string
      value: string
      max: string
      progress: number
      tooltip?: string
    }>
  }
  accountMargin: {
    balance: string
    equity: string
    profit: string
    profitTone: string
    freeMargin: string
    marginUsed: string
    marginUsedPct: string
    marginLevel: string
  }
  exposureHeat: {
    grossExposure: string
    netExposure: string
    maxSingleExposurePct: string
    currencyExposure: Array<{ label: string; value: string }>
    currencyWeights: Array<{ label: string; value: string }>
    avgCorrelation: string
    maxCorrelation: string
    hiddenOverlap: string
    redundancyScore: string
    effectiveIndependentBets: string
    diversificationRatio: string
  }
  regime: {
    aggregate: string
    confidence: string
    transitionChanged: string
    market: string
    volatility: string
    liquidity: string
    crisis: string
    warnings: string[]
    signals: string[]
  }
}

export function SessionOverviewCards({
  sessionDetails,
  strategyControl,
  riskMonitor,
  accountMargin,
  exposureHeat,
  regime,
}: SessionOverviewCardsProps) {
  
  return (
    <TooltipProvider>
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Session Details</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md bg-muted/50 p-2 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Session Number:</span>
              <span className="font-medium">{sessionDetails.sessionNumber}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Session Name:</span>
              <span className="font-medium">{sessionDetails.sessionName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Step:</span>
              <span className="font-medium">{sessionDetails.step}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Account Login:</span>
              <span className="font-medium">{sessionDetails.login}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Server:</span>
              <span className="font-medium">{sessionDetails.server}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Leverage:</span>
              <span className="font-medium">{sessionDetails.leverage}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Commission:</span>
              <span className="font-medium">{sessionDetails.commission}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Slippage Type:</span>
              <span className="font-medium">{sessionDetails.slippageType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Spread type:</span>
              <span className="font-medium">{sessionDetails.spreadType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Data Resolution:</span>
              <span className="font-medium">{sessionDetails.dataResolution}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Strategy Control</CardTitle>
          <PlayCircle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md bg-muted/50 p-2 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Strategy:</span>
              <span className="font-medium">{strategyControl.strategyLabel}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Symbols:</span>
              <span className="font-medium">{strategyControl.symbols}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Timeframe:</span>
              <span className="font-medium">{strategyControl.timeframe}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-muted-foreground text-xs">Approved</div>
              <div className="font-mono font-bold text-emerald-500">{strategyControl.approvedCount}</div>
            </div>
            <div>
              <div className="text-muted-foreground text-xs">Rejected</div>
              <div className="font-mono font-bold text-red-500">{strategyControl.rejectedCount}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Risk Monitor</CardTitle>
          <ShieldAlert className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
            <span className="text-muted-foreground">VaR Cap</span>
            <Progress value={riskMonitor.varCap.progress} className="h-2 [&>div]:bg-emerald-500" />
            <span className="font-medium text-emerald-500 whitespace-nowrap">
              {riskMonitor.varCap.current} / {riskMonitor.varCap.limit}
            </span>
          </div>

          <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
            <span className="text-muted-foreground">CVaR Cap</span>
            <Progress value={riskMonitor.cvarCap.progress} className="h-2 [&>div]:bg-emerald-500" />
            <span className="font-medium text-emerald-500 whitespace-nowrap">
              {riskMonitor.cvarCap.current} / {riskMonitor.cvarCap.limit}
            </span>
          </div>

          {[
            ["Current Drawdown", riskMonitor.currentDrawdown],
            ["Max Drawdown", riskMonitor.maxDrawdown],
            ["Drawdown Velocity", riskMonitor.drawdownVelocity],
            ["Max Time Under Water", riskMonitor.timeUnderWater],
          ].map(([label, value]) => (
            <div
              key={label}
              className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm"
            >
              <span className="text-muted-foreground">{label}</span>
              <div className="h-2" />
              <span className="font-medium text-emerald-500 whitespace-nowrap">
                {value}
              </span>
            </div>
          ))}

          <div className="space-y-3">
            {riskMonitor.scores.map((score) => (
              <div
                key={score.key}
                className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm"
              >
                {score.tooltip ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className="cursor-help text-left text-muted-foreground underline decoration-dotted decoration-muted-foreground/50 underline-offset-4"
                      >
                        {score.label}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs whitespace-pre-wrap text-xs">
                      {score.tooltip}
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <span className="text-muted-foreground">{score.label}</span>
                )}
                <Progress value={score.progress} className="h-2 [&>div]:bg-emerald-500" />
                <span className="font-medium text-emerald-500 whitespace-nowrap">
                  {score.value} / {score.max}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Account &amp; Margin</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {[
                ["Balance", accountMargin.balance],
                ["Equity", accountMargin.equity],
                ["Free Margin", accountMargin.freeMargin],
                ["Margin Used", accountMargin.marginUsed],
                ["Margin Used %", accountMargin.marginUsedPct],
                ["Margin Level", accountMargin.marginLevel],
              ].map(([label, value]) => (
                <div key={label} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
                  <span className="text-muted-foreground">{label}</span>
                  <div className="h-2" />
                  <span className="font-medium text-emerald-500 whitespace-nowrap">{value}</span>
                </div>
              ))}
              <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
                <span className="text-muted-foreground">Profit</span>
                <div className="h-2" />
                <span className={`font-medium whitespace-nowrap ${accountMargin.profitTone}`}>
                  {accountMargin.profit}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exposure and Heat Metrics</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {[
                ["Gross Exposure", exposureHeat.grossExposure],
                ["Net Exposure", exposureHeat.netExposure],
                ["Max Single Exposure %", exposureHeat.maxSingleExposurePct],
                ["Avg Correlation", exposureHeat.avgCorrelation],
                ["Max Correlation", exposureHeat.maxCorrelation],
                ["Hidden Overlap", exposureHeat.hiddenOverlap],
                ["Redundancy Score", exposureHeat.redundancyScore],
                ["Effective Independent Bets", exposureHeat.effectiveIndependentBets],
                ["Diversification Ratio", exposureHeat.diversificationRatio],
              ].map(([label, value]) => (
                <div key={label} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
                  <span className="text-muted-foreground">{label}</span>
                  <div className="h-2" />
                  <span className="font-medium text-emerald-500 whitespace-nowrap">{value}</span>
                </div>
              ))}
            </div>

          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Regime</CardTitle>
            <ShieldAlert className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              {[
                ["Aggregate", regime.aggregate],
                ["Confidence", regime.confidence],
                ["Transition Changed", regime.transitionChanged],
                ["Market", regime.market],
                ["Volatility", regime.volatility],
                ["Liquidity", regime.liquidity],
                ["Crisis", regime.crisis],
              ].map(([label, value]) => (
                <div key={label} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
                  <span className="text-muted-foreground">{label}</span>
                  <div className="h-2" />
                  <span className="font-medium text-emerald-500 whitespace-nowrap">{value}</span>
                </div>
              ))}
            </div>
            {regime.warnings.length > 0 ? (
              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">Warnings</div>
                <div className="text-xs text-muted-foreground">{regime.warnings.join(" | ")}</div>
              </div>
            ) : null}
            {regime.signals.length > 0 ? (
              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">Signals Triggered</div>
                <div className="text-xs text-muted-foreground">{regime.signals.join(" | ")}</div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

    </div>
    </TooltipProvider>
  )
}
