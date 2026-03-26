"use client"

import { format } from "date-fns"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

interface WarmupControlsProps {
  warmupBy: "date" | "bars"
  onWarmupByChange: (value: "date" | "bars") => void
  warmupStartDate?: Date
  onWarmupStartDateChange: (value: Date | undefined) => void
  warmupBars: number
  onWarmupBarsChange: (value: number) => void
}

export function WarmupControls({
  warmupBy,
  onWarmupByChange,
  warmupStartDate,
  onWarmupStartDateChange,
  warmupBars,
  onWarmupBarsChange,
}: WarmupControlsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t">
      <div className="space-y-2">
        <Label htmlFor="warmupBy">Warmup Period</Label>
        <Select value={warmupBy} onValueChange={(value) => onWarmupByChange(value as "date" | "bars")}>
          <SelectTrigger id="warmupBy">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="date">By Date</SelectItem>
            <SelectItem value="bars">By Bars</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {warmupBy === "date" ? (
        <div className="space-y-2 flex flex-col md:col-span-2">
          <Label>Warmup Start Date</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !warmupStartDate && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {warmupStartDate ? format(warmupStartDate, "PPP") : <span>Pick a date</span>}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={warmupStartDate}
                onSelect={onWarmupStartDateChange}
                initialFocus
                captionLayout="dropdown"
                fromYear={2000}
                toYear={new Date().getFullYear() + 1}
              />
            </PopoverContent>
          </Popover>
          <p className="text-xs text-muted-foreground">
            Data will be downloaded from this date to calculate indicators, but trading starts at the Start Date
          </p>
        </div>
      ) : (
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="warmupBars">Warmup Bars</Label>
          <Input
            id="warmupBars"
            type="number"
            min="0"
            placeholder="e.g. 100"
            value={warmupBars}
            onChange={(e) => onWarmupBarsChange(parseInt(e.target.value, 10) || 0)}
          />
          <p className="text-xs text-muted-foreground">
            Number of bars before the trading period to use for indicator warmup
          </p>
        </div>
      )}
    </div>
  )
}
