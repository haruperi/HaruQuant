"use client"

import React from "react"
import { Camera, Download } from "lucide-react"
import { toPng } from "html-to-image"
import { Button } from "@/components/ui/button"
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger 
} from "@/components/ui/tooltip"
import { toast } from "sonner"

interface PerformanceActionsProps {
  data?: any
  filename?: string
  excludeKeys?: string[]
  containerId?: string
}

export function PerformanceActions({ 
  data, 
  filename = "haruquant-report", 
  excludeKeys = [],
  containerId = "performance-report-content"
}: PerformanceActionsProps) {
  
  const handleScreenshot = async () => {
    const element = document.getElementById(containerId)
    if (!element) {
      toast.error("Could not find content to capture")
      return
    }

    const toastId = toast.loading("Generating high-resolution snapshot...")
    
    try {
      // Ensure element is visible and stable
      const dataUrl = await toPng(element, { 
        backgroundColor: "#000",
        quality: 0.95,
        pixelRatio: 2, // High DPI
        filter: (node) => {
            // Exclude action buttons from the screenshot
            if (node.classList?.contains('performance-actions-exclude')) return false;
            return true;
        }
      })
      
      const link = document.createElement("a")
      link.download = `${filename}-${new Date().getTime()}.png`
      link.href = dataUrl
      link.click()
      toast.success("Snapshot saved", { id: toastId })
    } catch (err) {
      console.error("Screenshot failed", err)
      toast.error("Capture failed", { id: toastId })
    }
  }

  const handleExportCSV = () => {
    if (!data) {
      toast.error("No data available to export")
      return
    }

    try {
      const rows: string[] = []
      
      const flattenData = (obj: any, prefix = ""): any => {
        if (!obj) return {};
        return Object.keys(obj).reduce((acc: any, k: string) => {
          const pre = prefix.length ? prefix + "." : ""
          const val = obj[k]
          
          if (val && typeof val === "object" && !Array.isArray(val) && !(val instanceof Date)) {
            Object.assign(acc, flattenData(val, pre + k))
          } else {
            acc[pre + k] = val
          }
          return acc
        }, {})
      }

      const flat = flattenData(data)
      const headers = Object.keys(flat).filter(k => !excludeKeys.includes(k))
      
      rows.push(headers.join(","))
      rows.push(headers.map(h => {
        const val = flat[h]
        if (val === null || val === undefined) return ""
        return `"${String(val).replace(/"/g, '""')}"`
      }).join(","))

      const csvContent = "data:text/csv;charset=utf-8," + rows.join("\n")
      const encodedUri = encodeURI(csvContent)
      const link = document.createElement("a")
      link.setAttribute("href", encodedUri)
      link.setAttribute("download", `${filename}-${new Date().getTime()}.csv`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      toast.success("Data exported to CSV")
    } catch (err) {
      console.error("CSV export failed", err)
      toast.error("Export failed")
    }
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="performance-actions-exclude flex items-center gap-1 bg-muted/40 p-1 rounded-lg border shadow-sm backdrop-blur-sm">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleScreenshot}
              className="hover:bg-background hover:text-primary transition-colors"
            >
              <Camera className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-[10px] py-1 px-2">Capture View</TooltipContent>
        </Tooltip>

        <div className="w-[1px] h-3 bg-border mx-0.5" />

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleExportCSV}
              className="hover:bg-background hover:text-primary transition-colors"
            >
              <Download className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="text-[10px] py-1 px-2">Export Data</TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  )
}
