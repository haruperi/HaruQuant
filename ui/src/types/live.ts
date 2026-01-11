/**
 * TypeScript types for Live Trading
 *
 * Matches the Pydantic models from the backend API
 */

export interface LiveSession {
  session_id: number
  user_id: number
  session_name: string
  status: SessionStatus
  mode: TradingMode
  max_total_risk_pct: number
  max_positions: number
  max_correlation: number
  max_drawdown_pct: number
  trading_hours_start: string | null
  trading_hours_end: string | null
  allowed_days: string | null
  started_at: string | null
  stopped_at: string | null
  last_heartbeat: string | null
  error_message: string | null
  total_signals_detected: number
  total_signals_executed: number
  total_signals_rejected: number
  created_at: string
  updated_at: string
}

export type SessionStatus = "stopped" | "starting" | "running" | "paused" | "stopping" | "error"
export type TradingMode = "paper" | "live"

export interface SessionCreateRequest {
  session_name: string
  mode?: TradingMode
  max_total_risk_pct?: number
  max_positions?: number
  max_correlation?: number
  max_drawdown_pct?: number
  trading_hours_start?: string
  trading_hours_end?: string
  allowed_days?: string
}

export interface SessionUpdateRequest {
  session_name?: string
  mode?: TradingMode
  max_total_risk_pct?: number
  max_positions?: number
  max_correlation?: number
  max_drawdown_pct?: number
  trading_hours_start?: string
  trading_hours_end?: string
  allowed_days?: string
}

export interface SessionStatusInfo {
  session_id: number
  session_name: string
  status: SessionStatus
  running: boolean
  paused: boolean
  signals_detected: number
  signals_approved: number
  signals_rejected: number
  positions_opened: number
  positions_closed: number
  active_positions: number
  current_equity: number
  current_balance: number
  account_name?: string
  account_server?: string
  account_login?: number
  daily_pnl?: number
  daily_pnl_limit?: number
  current_drawdown_pct?: number
  max_drawdown_pct?: number
}

export interface SessionStatistics {
  session: {
    session_id: number
    session_name: string
    status: SessionStatusInfo
    running: boolean
    paused: boolean
    start_time: string
    uptime_seconds: number
    errors_count: number
  }
  health: {
    last_health_check: string
    mt5_connected: boolean
    components_healthy: boolean
  }
  signals: {
    total_detected: number
    total_approved: number
    total_rejected: number
    approval_rate: number
  }
  positions: {
    total_opened: number
    total_closed: number
  }
  signal_engine: Record<string, any>
  risk_manager: Record<string, any>
  execution_engine: Record<string, any>
  trade_manager: Record<string, any>
}

export interface Signal {
  signal_id: number
  session_id: number
  strategy_version_id: number
  symbol: string
  timeframe: string
  signal_type: "buy" | "sell"
  signal_time: string
  entry_price: number | null
  stop_loss: number | null
  take_profit: number | null
  risk_pips: number | null
  risk_usd: number | null
  position_size: number | null
  reward_risk_ratio: number | null
  signal_reason: string | null
  status: SignalStatus
  rejection_reason: string | null
  created_at: string
}

export type SignalStatus = "pending" | "approved" | "rejected" | "executed" | "failed"

export interface Position {
  position_id: number
  session_id: number
  signal_id: number | null
  mt5_ticket: number | null
  mt5_order: number | null
  symbol: string
  type: "buy" | "sell"
  open_time: string
  open_price: number
  position_size: number
  current_price: number | null
  current_profit: number | null
  current_profit_pct: number | null
  initial_stop_loss: number | null
  current_stop_loss: number | null
  initial_take_profit: number | null
  current_take_profit: number | null
  breakeven_activated: boolean
  trailing_stop_activated: boolean
  partial_close_count: number
  status: PositionStatus
  close_reason: string | null
  close_time: string | null
  close_price: number | null
  final_profit: number | null
  final_profit_pct: number | null
  created_at: string
  updated_at: string
}

export type PositionStatus = "open" | "modified" | "closing" | "closed"

export interface PositionModifyRequest {
  stop_loss?: number
  take_profit?: number
}

export interface ManualOrderRequest {
  symbol: string
  volume: number
  type: "buy" | "sell"
  sl_pips?: number
  tp_pips?: number
  comment?: string
}

export interface SessionStrategy {
  id: number
  session_id: number
  strategy_version_id: number
  strategy_name: string
  version: string
  is_active: boolean
  symbols: string[]
  timeframes: string[]
  max_risk_per_trade_pct: number
  position_size_type: "risk" | "fixed" | "percent"
  position_size_value: number
  strategy_params: Record<string, any> | null
  created_at: string
}

export interface StrategyAddRequest {
  strategy_version_id: number
  symbols: string[]
  timeframes: string[]
  max_risk_per_trade_pct?: number
  position_size_type?: "risk" | "fixed" | "percent"
  position_size_value?: number
  strategy_params?: Record<string, any>
}

// WebSocket event types
export interface WebSocketMessage {
  type: string
  session_id?: number
  data?: any
  [key: string]: any
}

export interface SignalDetectedEvent extends WebSocketMessage {
  type: "signal_detected"
  data: Signal
}

export interface SignalApprovedEvent extends WebSocketMessage {
  type: "signal_approved"
  data: Signal
}

export interface SignalRejectedEvent extends WebSocketMessage {
  type: "signal_rejected"
  data: Signal
  reason: string
}

export interface PositionOpenedEvent extends WebSocketMessage {
  type: "position_opened"
  data: Position
}

export interface PositionUpdatedEvent extends WebSocketMessage {
  type: "position_updated"
  data: Position
}

export interface PositionClosedEvent extends WebSocketMessage {
  type: "position_closed"
  data: Position
  reason: string
}

export interface StatusUpdateEvent extends WebSocketMessage {
  type: "status"
  data: SessionStatusInfo
}

export interface LogMessageEvent extends WebSocketMessage {
  type: "logs"
  level: "info" | "warning" | "error" | "critical"
  category: "signal" | "risk" | "execution" | "trade_mgmt" | "system"
  message: string
  details: Record<string, any> | null
  timestamp: number
}

export interface SubscriptionUpdatedEvent extends WebSocketMessage {
  type: "subscription_updated"
  channels: string[]
}

export type LiveWebSocketEvent =
  | SignalDetectedEvent
  | SignalApprovedEvent
  | SignalRejectedEvent
  | PositionOpenedEvent
  | PositionUpdatedEvent
  | PositionClosedEvent
  | StatusUpdateEvent
  | LogMessageEvent
  | SubscriptionUpdatedEvent
