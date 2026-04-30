import Highcharts from "highcharts/highstock"

export function registerSwingTrendLines(hc: typeof Highcharts) {
  // Ensure we don't register twice
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if ((hc as any).seriesTypes && (hc as any).seriesTypes.swingtrendlines) {
    return;
  }

  hc.seriesType(
    "swingtrendlines",
    "sma",
    {
      name: "Swing Trend Lines",
      params: {
        timeframe: 60, // Swing TimeFrame in minutes
      },
      marker: {
        enabled: false,
      },
      // Default to bullish color, zones will override
      color: "#26A69A",
      lineWidth: 3,
      zoneAxis: "x",
    },
    {
      nameBase: "Swing Trend Lines",
      nameComponents: ["timeframe"],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      getValues: function (series: any, params: any) {
        const xData = series.xData as number[];
        const yData = series.yData as number[][]; // [open, high, low, close]
        
        if (!xData || !yData || xData.length === 0) {
          return undefined;
        }

        const timeframeMs = ((params.timeframe as number) || 60) * 60 * 1000;
        const values: number[][] = [];
        const xDataOut: number[] = [];
        const yDataOut: number[] = [];
        
        let highestHigh_Stat: number | null = null;
        let lowestLow_Stat: number | null = null;
        let upswingSupport_Stat: number | null = null;
        let downswingResistance_Stat: number | null = null;
        let swingDirection_Stat = 0; // 1 for upswing, 0 for downswing
        
        let lastBucket = -1;
        
        let sec_prev_h: number | null = null;
        let sec_prev_l: number | null = null;
        
        let currentBucketHigh = -Infinity;
        let currentBucketLow = Infinity;

        const zones: Array<{value?: number, color: string}> = [];
        let lastDirection = -1;

        for (let i = 0; i < xData.length; i++) {
          const t = xData[i];
          const high = yData[i][1];
          const low = yData[i][2];
          
          const bucket = Math.floor(t / timeframeMs);
          let isNewSwingBar = false;

          if (bucket !== lastBucket) {
            isNewSwingBar = true;
            if (lastBucket !== -1) {
              sec_prev_h = currentBucketHigh;
              sec_prev_l = currentBucketLow;
            }
            lastBucket = bucket;
            currentBucketHigh = high;
            currentBucketLow = low;
          } else {
            currentBucketHigh = Math.max(currentBucketHigh, high);
            currentBucketLow = Math.min(currentBucketLow, low);
          }

          const currentSwingHigh = currentBucketHigh;
          const currentSwingLow = currentBucketLow;

          if (isNewSwingBar) {
            if (highestHigh_Stat === null) {
              if (sec_prev_h !== null && sec_prev_l !== null) {
                highestHigh_Stat = sec_prev_h;
                lowestLow_Stat = sec_prev_l;
                upswingSupport_Stat = sec_prev_l;
                downswingResistance_Stat = sec_prev_h;
                swingDirection_Stat = 0;
              } else if (currentSwingHigh !== -Infinity) {
                highestHigh_Stat = currentSwingHigh;
                lowestLow_Stat = currentSwingLow;
                upswingSupport_Stat = currentSwingLow;
                downswingResistance_Stat = currentSwingHigh;
                swingDirection_Stat = 0;
              }
            }
          }

          if (highestHigh_Stat !== null) {
            if (swingDirection_Stat === 1) { // upswing
              if (currentSwingHigh > highestHigh_Stat) {
                highestHigh_Stat = currentSwingHigh;
              }
              if (upswingSupport_Stat !== null && currentSwingLow > upswingSupport_Stat) {
                upswingSupport_Stat = currentSwingLow;
              }
              if (upswingSupport_Stat !== null && currentSwingHigh < upswingSupport_Stat) {
                swingDirection_Stat = 0;
                lowestLow_Stat = currentSwingLow;
                downswingResistance_Stat = currentSwingHigh;
              }
            } else { // downswing
              if (lowestLow_Stat === null || currentSwingLow < lowestLow_Stat) {
                lowestLow_Stat = currentSwingLow;
              }
              if (downswingResistance_Stat !== null && currentSwingHigh < downswingResistance_Stat) {
                downswingResistance_Stat = currentSwingHigh;
              }
              if (downswingResistance_Stat !== null && currentSwingLow > downswingResistance_Stat) {
                swingDirection_Stat = 1;
                highestHigh_Stat = currentSwingHigh;
                upswingSupport_Stat = currentSwingLow;
              }
            }
          }

          let plotValue: number | null = null;
          if (swingDirection_Stat === 1) {
            plotValue = upswingSupport_Stat;
          } else if (swingDirection_Stat === 0) {
            plotValue = downswingResistance_Stat;
          }

          xDataOut.push(t);
          yDataOut.push(plotValue === null ? NaN : plotValue);
          values.push([t, plotValue === null ? NaN : plotValue]);

          // Handle zones for colors
          if (swingDirection_Stat !== lastDirection) {
            if (lastDirection !== -1) {
               zones.push({
                 value: t,
                 color: lastDirection === 1 ? "#26A69A" : "#EF5350"
               });
            }
            lastDirection = swingDirection_Stat;
          }
        }

        // Add final zone covering the rest of the chart
        zones.push({
          color: lastDirection === 1 ? "#26A69A" : "#EF5350"
        });

        // Set the zones on the indicator series options dynamically
        this.options.zones = zones;

        return {
          xData: xDataOut,
          yData: yDataOut,
          values: values
        };
      }
    }
  );
}
