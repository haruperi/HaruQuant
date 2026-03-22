export type PendingOrderType =
  | "buy_limit"
  | "sell_limit"
  | "buy_stop"
  | "sell_stop"
  | "buy_stop_limit"
  | "sell_stop_limit"

export interface PendingOrderValidationInput {
  type: string
  price?: number | null
  sl?: number | null
  tp?: number | null
  volume?: number | null
  currentPrice?: number | null
  maxVolume?: number | null
}

function isBuyOrder(type: string) {
  return type.startsWith("buy")
}

function normalizeOptionalNumber(value?: number | null) {
  if (value === null || value === undefined || value === 0) return null
  return value
}

export function validatePendingOrder(input: PendingOrderValidationInput): string | null {
  const price = normalizeOptionalNumber(input.price)
  const sl = normalizeOptionalNumber(input.sl)
  const tp = normalizeOptionalNumber(input.tp)
  const volume = normalizeOptionalNumber(input.volume)
  const currentPrice = normalizeOptionalNumber(input.currentPrice)
  const maxVolume = normalizeOptionalNumber(input.maxVolume)
  const type = String(input.type || "").toLowerCase()

  if (volume !== null && volume <= 0) {
    return "Volume must be greater than zero."
  }

  if (maxVolume !== null && volume !== null && volume > maxVolume) {
    return `Volume cannot exceed ${maxVolume.toFixed(2)}.`
  }

  if (price !== null && price <= 0) {
    return "Price must be greater than zero."
  }

  if (sl !== null && sl <= 0) {
    return "Stop Loss must be greater than zero."
  }

  if (tp !== null && tp <= 0) {
    return "Take Profit must be greater than zero."
  }

  if (currentPrice !== null && price !== null) {
    if (type === "buy_limit" && price >= currentPrice) {
      return "Buy Limit price must be below the current price."
    }
    if (type === "sell_limit" && price <= currentPrice) {
      return "Sell Limit price must be above the current price."
    }
    if (type === "buy_stop" && price <= currentPrice) {
      return "Buy Stop price must be above the current price."
    }
    if (type === "sell_stop" && price >= currentPrice) {
      return "Sell Stop price must be below the current price."
    }
    if (type === "buy_stop_limit" && price <= currentPrice) {
      return "Buy Stop Limit trigger must be above the current price."
    }
    if (type === "sell_stop_limit" && price >= currentPrice) {
      return "Sell Stop Limit trigger must be below the current price."
    }
  }

  if (price !== null && sl !== null) {
    if (isBuyOrder(type) && sl >= price) {
      return "For buy orders, Stop Loss must be below the entry price."
    }
    if (!isBuyOrder(type) && sl <= price) {
      return "For sell orders, Stop Loss must be above the entry price."
    }
  }

  if (price !== null && tp !== null) {
    if (isBuyOrder(type) && tp <= price) {
      return "For buy orders, Take Profit must be above the entry price."
    }
    if (!isBuyOrder(type) && tp >= price) {
      return "For sell orders, Take Profit must be below the entry price."
    }
  }

  return null
}
