"use client"

import { useEffect, useRef } from "react"
import { createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries, Time, SeriesMarker, createSeriesMarkers } from "lightweight-charts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const PriceChart = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current!.clientWidth })
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      width: chartContainerRef.current.clientWidth,
      height: 750,
      grid: {
        vertLines: { color: 'rgba(42, 46, 57, 0.1)' },
        horzLines: { color: 'rgba(42, 46, 57, 0.1)' },
      },
      rightPriceScale: {
         borderColor: 'rgba(42, 46, 57, 0.1)',
      },
      timeScale: {
         borderColor: 'rgba(42, 46, 57, 0.1)',
         timeVisible: true,
      }
    })

    // 1. Candlestick Series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    })

    // Mock Data Generator
    const data = []
    let time = 1672531200 // 2023-01-01
    let price = 16500
    for (let i = 0; i < 300; i++) {
        const volatility = 50 + Math.random() * 50
        const change = (Math.random() - 0.5) * volatility
        const open = price
        const close = price + change
        const high = Math.max(open, close) + Math.random() * 20
        const low = Math.min(open, close) - Math.random() * 20

        data.push({ time: time as Time, open, high, low, close })
        time += 3600 // 1 hour
        price = close
    }
    candlestickSeries.setData(data)

    // 2. Indicators: SMA 20 (Blue Line)
    const smaSeries = chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1 })
    const smaData = data.map((d, i, arr) => {
        if (i < 20) return null
        const sum = arr.slice(i - 20, i).reduce((acc, val) => acc + val.close, 0)
        return { time: d.time, value: sum / 20 }
    }).filter(d => d !== null) as any
    smaSeries.setData(smaData)

    // 3. Indicators: EMA 50 (Orange Line)
    const emaSeries = chart.addSeries(LineSeries, { color: '#f97316', lineWidth: 1 })
    // Simple mock EMA calculation
    const emaData = data.map((d, i) => {
         // rough mock
         return { time: d.time, value: d.close * 0.95 + (Math.random() * 50)}
    })
    emaSeries.setData(emaData)


    // 4. Trade Markers (Buy/Sell)
    const markers: SeriesMarker<Time>[] = []
    // Add random Buy/Send signals
    for (let i = 30; i < 300; i += 25) {
        const isBuy = Math.random() > 0.5
        markers.push({
            time: data[i].time,
            position: isBuy ? 'belowBar' : 'aboveBar',
            color: isBuy ? '#10b981' : '#ef4444',
            shape: isBuy ? 'arrowUp' : 'arrowDown',
            text: isBuy ? 'Buy' : 'Sell',
            size: 1
        })
    }
    createSeriesMarkers(candlestickSeries, markers)

    // 5. Volume
    const volumeSeries = chart.addSeries(HistogramSeries, {
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '', // overlay
    })
    volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
    });
    const volumeData = data.map(d => ({
        time: d.time,
        value: Math.random() * 100,
        color: d.close >= d.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'
    }))
    volumeSeries.setData(volumeData)


    chart.timeScale().fitContent()

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  return (
    <Card className="w-full">
        <CardHeader>
            <CardTitle>Trade Analysis (Price Action)</CardTitle>
        </CardHeader>
        <CardContent>
             <div ref={chartContainerRef} className="w-full h-[750px]" />
        </CardContent>
    </Card>
  )
}
