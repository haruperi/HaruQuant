"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import type { CurrencyStrength } from "@/types/live"

interface CurrencyStrengthCardProps {
  data: CurrencyStrength
}

export function CurrencyStrengthCard({ data }: CurrencyStrengthCardProps) {
  const { currency, strength, rank, trend, confidence } = data

  // Determine trend direction and styling
  const isBullish = strength > 0
  const isNeutral = Math.abs(strength) < 0.1
  const isStrong = Math.abs(strength) > 0.5

  // Trend colors based on strength
  const getTrendColor = () => {
    if (isNeutral) return "text-muted-foreground"
    if (isBullish) {
      return isStrong ? "text-emerald-500" : "text-emerald-400"
    } else {
      return isStrong ? "text-red-500" : "text-red-400"
    }
  }

  const getBgColor = () => {
    if (isNeutral) return "bg-muted/50"
    if (isBullish) {
      return isStrong ? "bg-emerald-500/10" : "bg-emerald-500/5"
    } else {
      return isStrong ? "bg-red-500/10" : "bg-red-500/5"
    }
  }

  // Trend icon
  const TrendIcon = isNeutral ? Minus : isBullish ? TrendingUp : TrendingDown

  // Badge variant and text
  const getBadgeProps = () => {
    switch (trend) {
      case "strong_buy":
        return {
          className: "bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30",
          text: "STRONG BUY"
        }
      case "buy":
        return {
          className: "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20",
          text: "BUY"
        }
      case "neutral":
        return {
          className: "bg-muted/50 text-muted-foreground hover:bg-muted/70",
          text: "NEUTRAL"
        }
      case "sell":
        return {
          className: "bg-red-500/10 text-red-500 hover:bg-red-500/20",
          text: "SELL"
        }
      case "strong_sell":
        return {
          className: "bg-red-500/20 text-red-500 hover:bg-red-500/30",
          text: "STRONG SELL"
        }
      default:
        return {
          className: "bg-muted/50 text-muted-foreground",
          text: "UNKNOWN"
        }
    }
  }

  const badgeProps = getBadgeProps()

  // Rank styling
  const getRankBadgeColor = () => {
    if (rank === 1) return "bg-yellow-500/20 text-yellow-500 border-yellow-500/30"
    if (rank === 2) return "bg-slate-400/20 text-slate-400 border-slate-400/30"
    if (rank === 3) return "bg-amber-700/20 text-amber-700 border-amber-700/30"
    if (rank >= 7) return "bg-red-500/10 text-red-500 border-red-500/20"
    return "bg-muted/50 text-muted-foreground border-muted"
  }

  return (
    <Card className={`transition-all hover:shadow-md ${getBgColor()} border-2`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold">{currency}</CardTitle>
          <Badge
            variant="outline"
            className={`text-xs font-semibold ${getRankBadgeColor()}`}
          >
            #{rank}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Strength Meter */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-muted-foreground font-medium">
              Strength
            </span>
            <span className={`font-bold text-lg ${getTrendColor()}`}>
              {strength > 0 ? "+" : ""}
              {strength.toFixed(2)}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="relative w-full h-3 bg-muted rounded-full overflow-hidden">
            {/* Center line */}
            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-border z-10" />

            {/* Strength bar */}
            <div
              className={`absolute top-0 bottom-0 transition-all duration-300 ${
                isBullish
                  ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                  : "bg-gradient-to-l from-red-500 to-red-400"
              }`}
              style={{
                [isBullish ? "left" : "right"]: "50%",
                width: `${Math.min(Math.abs(strength), 50)}%`,
              }}
            />
          </div>

          {/* Scale labels */}
          <div className="flex justify-between mt-1">
            <span className="text-xs text-red-500">-1%</span>
            <span className="text-xs text-muted-foreground">0</span>
            <span className="text-xs text-emerald-500">+1%</span>
          </div>
        </div>

        {/* Trend Badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <TrendIcon className={`h-5 w-5 ${getTrendColor()}`} />
            <Badge className={`${badgeProps.className} font-semibold`}>
              {badgeProps.text}
            </Badge>
          </div>
        </div>

        {/* Confidence Meter */}
        <div className="pt-3 border-t">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-muted-foreground font-medium">
              Confidence
            </span>
            <span className="text-sm font-bold">{confidence.toFixed(0)}%</span>
          </div>

          <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-300"
              style={{ width: `${confidence}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
