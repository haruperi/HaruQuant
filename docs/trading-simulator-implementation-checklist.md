# Trading Simulator Implementation Checklist

## Overview

Build a comprehensive trading simulator page that simulates live trading with real-time chart playback at variable speeds (1-1440 bars/second). Supports manual trading (buttons + chart clicks), automatic trading (strategy execution + trade replay), and full persistence to database.

## User Requirements Confirmed

- ✅ Use existing backend TradeSimulator (MT5-aligned)
- ✅ Both manual trading options (buttons + chart clicks)
- ✅ Both auto modes (strategy execution + trade replay)
- ✅ Save all simulations to database
- ✅ Default speed: X1 (1 bar/sec)
- ✅ Resume capability after browser close
- ✅ Trade notifications (sound/desktop alerts)
- ✅ Auto-delete old sessions (7+ days)
- ✅ Chart indicators overlay (SMA/EMA/RSI)
- ✅ Skip to date/time functionality

---

## Phase 1: Backend Foundation

### 1.1 Database Schema

- [X] Extend `apps/sqlite/schema.py` with `simulation_sessions` table
- [X] Extend `apps/sqlite/schema.py` with `simulation_trades` table
- [X] Create database migration script
- [X] Test schema with SQLite browser

### 1.2 Database Operations

- [X] Create `apps/sqlite/simulator.py`
- [X] Implement `create_session(config)` method
- [X] Implement `save_trade(session_id, trade)` method
- [X] Implement `update_session_status(session_id, status)` method
- [X] Implement `get_session_trades(session_id)` method
- [X] Implement `save_session_state(session_id, current_bar_index)` method for resume
- [X] Implement `get_paused_sessions(user_id)` method for resume
- [X] Add unit tests for database operations

### 1.3 Simulation Session Manager

- [X] Create `apps/simulator/session.py`
- [X] Implement `SimulatorSession.__init__()` with config
- [X] Implement `load_historical_bars()` method
- [X] Implement `start_stream(websocket)` method with asyncio loop
- [X] Implement variable speed delay: `asyncio.sleep(1.0 / speed_multiplier)`
- [X] Implement `_process_bar(bar)` method (update sim, check SL/TP)
- [X] Implement pause/resume functionality (`is_paused` flag)
- [X] Implement `save_state()` method to persist current_bar_index
- [X] Implement `seek_to_bar(bar_index)` method for skip functionality
- [X] Add real-time indicator calculations (SMA/EMA/RSI) in bar processing
- [X] Test session manager independently (no API)

### 1.4 Automatic Trading Modes

- [X] Implement `_execute_strategy(bar)` method for strategy mode
- [X] Implement `_replay_trades(bar)` method for replay mode
- [X] Test strategy execution with sample strategy
- [X] Test trade replay with sample backtest trades

### 1.5 API Routes

- [X] Create `apps/api/routes/simulator.py`
- [X] Implement `POST /api/simulator/start` endpoint
- [X] Implement `GET /api/simulator/{session_id}` endpoint
- [X] Implement `PUT /api/simulator/{session_id}` endpoint (speed, pause)
- [X] Implement `POST /api/simulator/{session_id}/trade` endpoint
- [X] Implement `POST /api/simulator/{session_id}/resume` endpoint
- [X] Implement `POST /api/simulator/{session_id}/seek` endpoint (skip to date)
- [X] Implement `DELETE /api/simulator/{session_id}` endpoint
- [X] Implement `GET /api/simulator/sessions` endpoint (list sessions)
- [X] Implement `GET /api/simulator/paused` endpoint (get paused sessions for resume)
- [X] Implement WebSocket endpoint `WS /api/simulator/ws/{session_id}/stream`
- [X] Add WebSocket message types: bar, trade, account, indicator, completed
- [X] Add in-memory session store: `active_sessions: dict[int, SimulatorSession]`
- [X] Test all endpoints with Postman/curl

### 1.6 Background Jobs

- [X] Create `apps/scheduler.py` with APScheduler
- [X] Implement daily cleanup job for old sessions (7+ days)
- [X] Test cleanup job manually
- [X] Add scheduler to application startup

---

## Phase 2: Frontend Structure

### 2.1 API Client

- [X] Create `ui/src/lib/api/simulator.ts`
- [X] Define TypeScript interfaces: `SimulationConfig`, `SimulationSession`, `TradeRequest`
- [X] Implement `startSession(config)` method
- [X] Implement `getSession(sessionId)` method
- [X] Implement `updateSession(sessionId, update)` method
- [X] Implement `executeTrade(sessionId, trade)` method
- [X] Implement `resumeSession(sessionId)` method
- [X] Implement `seekToBar(sessionId, barIndex)` method
- [X] Implement `getPausedSessions()` method
- [X] Add error handling with proper types
- [X] Test API client with backend running

### 2.2 Main Page

- [X] Create `ui/src/app/(dashboard)/simulation/page.tsx`
- [X] Implement view state machine: config | execution | results
- [X] Implement `handleStart(sessionId, config)` transition to execution
- [X] Implement `handleComplete()` transition to results
- [X] Implement `handleBackToConfig()` reset
- [X] Add page header with title and description
- [X] Test view transitions

### 2.3 Configuration Form

- [X] Create `ui/src/components/simulation/config-form.tsx`
- [X] Add symbol input field
- [X] Add timeframe selector (M1, M5, M15, H1, H4, D1)
- [X] Add date range picker (start date, end date)
- [X] Add initial balance input
- [X] Add mode toggle: manual | strategy | replay
- [X] Add conditional strategy selector (for strategy mode)
- [X] Add conditional backtest selector (for replay mode)
- [X] Add speed preset selector (default: X1)
- [X] Add form validation before submit
- [X] Implement "Resume Session" button (if paused sessions exist)
- [X] Test form submission and validation

---

## Phase 3: Real-Time Chart Component

### 3.1 Chart Component

- [X] Create `ui/src/components/simulation/simulation-chart.tsx`
- [X] Initialize lightweight-charts with `createChart()`
- [X] Add candlestick series with green/red colors
- [X] Implement WebSocket connection to `/api/simulator/ws/{sessionId}/stream`
- [X] Handle `bar` messages: update chart with `.update()`
- [X] Handle `trade` messages: add entry/exit markers
- [X] Handle `indicator` messages: overlay SMA/EMA/RSI lines
- [X] Implement chart click handler for manual trading
- [X] Add trade marker overlays (HTML divs with arrows)
- [X] Add ResizeObserver for responsive sizing
- [X] Implement proper cleanup in useEffect return
- [X] Test chart at various speeds (X1, X60, X1440)

### 3.2 Indicator Overlay

- [X] Add indicator series (LineSeries for SMA, EMA, RSI)
- [X] Add indicator toggle switches in chart toolbar
- [X] Update indicators in real-time from WebSocket messages
- [X] Style indicators with distinct colors (SMA: blue, EMA: orange, RSI: purple)
- [ ] Test indicator visibility toggles

---

## Phase 4: Trading Controls

### 4.1 Speed Control

- [X] Create `ui/src/components/simulation/speed-control.tsx`
- [X] Add speed preset buttons: X1, X5, X15, X30, X60, X120, X240, X720, X1440
- [ ] Add Play/Pause button with icon toggle
- [X] Implement `updateSpeed()` API call
- [X] Implement `togglePause()` API call
- [X] Add current speed label display
- [X] Test all speed presets
- [X] Test pause/resume functionality

### 4.2 Skip to Date Control

- [X] Add date/time picker above chart
- [X] Add "Jump to Date" button
- [X] Implement `seekToBar()` API call
- [X] Calculate bar_index from selected date
- [X] Update chart and session state after seek
- [X] Test seeking to various dates

### 4.3 Trading Panel

- [X] Create `ui/src/components/simulation/trading-panel.tsx`
- [X] Add lot size input field
- [X] Add stop loss input field
- [X] Add take profit input field
- [X] Add current bid/ask price display
- [X] Add BUY button (green)
- [X] Add SELL button (red)
- [X] Implement `executeTrade()` API call
- [X] Add "Chart Click Trading" toggle switch
- [X] Disable buttons when chart-click mode enabled
- [X] Add toast notifications for trade success/failure
- [ ] Test button-based trading

### 4.4 Trade Dialog (Chart-Click)

- [X] Create `ui/src/components/simulation/trade-dialog.tsx`
- [X] Add dialog with trade type selector (Buy/Sell)
- [X] Add lot size, SL, TP inputs
- [X] Pre-fill price from chart click location
- [X] Implement submit handler with `executeTrade()` API call
- [X] Add validation before submission
- [ ] Test chart-click → dialog → trade execution flow

### 4.5 Trade Notifications

- [X] Add browser Notification API permission request
- [ ] Add sound files (buy.mp3, sell.mp3) to public/sounds/
- [X] Play sound on trade execution (if notifications enabled)
- [X] Show desktop notification with trade details
- [X] Add notification toggle in user settings/preferences
- [ ] Test notifications in different browsers

---

## Phase 5: Position & Account Management

### 5.1 Positions Panel

- [X] Create `ui/src/components/simulation/positions-panel.tsx`
- [ ] Display list of open positions from WebSocket updates
- [X] Show columns: Symbol, Type, Volume, Open Price, Current Price, P&L
- [X] Add close position button per row
- [ ] Update positions in real-time
- [ ] Test position updates and closure

### 5.2 Orders Panel

- [X] Create `ui/src/components/simulation/orders-panel.tsx`
- [X] Display list of pending orders
- [X] Show columns: Symbol, Type, Volume, Price, SL, TP
- [X] Add cancel order button per row
- [ ] Update orders in real-time (WebSocket)
- [ ] Test order placement and cancellation

### 5.3 Account Metrics Bar

- [X] Create `ui/src/components/simulation/account-metrics.tsx`
- [X] Display balance, equity, margin, profit in grid layout
- [X] Color-code profit (green if positive, red if negative)
- [ ] Update metrics in real-time from WebSocket
- [ ] Test metrics update accuracy

---

## Phase 6: Execution View Container

### 6.1 Execution View

- [X] Create `ui/src/components/simulation/execution-view.tsx`
- [X] Add WebSocket connection for account updates
- [X] Manage state: currentSpeed, chartClickEnabled, currentPrice, accountState
- [X] Implement layout: Speed control (top), Chart (left 70%), Panels (right 30%)
- [X] Handle chart click events
- [X] Show trade dialog on chart click (if enabled)
- [ ] Handle WebSocket "completed" message → transition to results
- [X] Add stop simulation button
- [ ] Test full execution flow from start to completion

---

## Phase 7: Results View

### 7.1 Results View

- [X] Create `ui/src/components/simulation/results-view.tsx`
- [X] Fetch session results from API
- [X] Display performance metrics grid: Final Balance, Total Trades, Win Rate, etc.
- [X] Add trades history table
- [X] Add "View Detailed Report" button (navigate to performance page)
- [X] Add "New Simulation" button (back to config)
- [ ] Test results display with completed simulation

---

## Phase 8: Testing & Polish

### 8.1 End-to-End Testing

- [ ] Test full manual trading flow (config → execute trades → results)
- [ ] Test strategy execution mode with real strategy
- [ ] Test trade replay mode with real backtest
- [ ] Test all speed presets (X1 through X1440)
- [ ] Test pause/resume across all modes
- [ ] Test skip to date functionality
- [ ] Test resume session after browser close
- [ ] Test chart-click trading
- [ ] Test indicators overlay
- [ ] Test notifications (sound + desktop)
- [ ] Test on mobile (responsive layout)
- [ ] Test WebSocket reconnection on disconnect
- [ ] Test error handling (bad symbol, no data, API errors)

### 8.2 Performance Testing

- [ ] Test chart rendering at X1440 speed (should not freeze UI)
- [ ] Test with large datasets (10k+ bars)
- [ ] Check memory usage over long simulations
- [ ] Verify WebSocket doesn't leak connections
- [ ] Test concurrent simulations (multiple sessions)

### 8.3 Bug Fixes & Edge Cases

- [ ] Handle missing historical data gracefully
- [ ] Handle WebSocket disconnects with reconnection
- [ ] Handle trade failures with proper error messages
- [ ] Handle zero balance / margin call scenarios
- [ ] Handle invalid SL/TP values
- [ ] Add loading states for all async operations
- [ ] Add error boundaries for React components

### 8.4 UI/UX Polish

- [ ] Add loading spinners where appropriate
- [ ] Add skeleton loaders for charts
- [ ] Improve mobile layout (hide panels, show only chart)
- [ ] Add keyboard shortcuts (Space: pause/resume, Arrow keys: speed adjust)
- [ ] Add tooltips for all buttons/controls
- [ ] Improve error messages to be user-friendly
- [ ] Add confirmation dialog before stopping simulation
- [ ] Test accessibility (keyboard navigation, screen readers)

---

## Phase 9: Documentation

### 9.1 Code Documentation

- [ ] Add docstrings to all backend classes/methods
- [ ] Add JSDoc comments to all frontend components
- [ ] Document WebSocket message protocol
- [ ] Document API endpoints with examples

### 9.2 User Documentation

- [ ] Create user guide: Getting Started with Simulator
- [ ] Document manual trading workflow
- [ ] Document strategy execution workflow
- [ ] Document trade replay workflow
- [ ] Add troubleshooting section
- [ ] Create video tutorial (optional)

---

## Phase 10: Deployment

### 10.1 Backend Deployment

- [ ] Run database migrations
- [ ] Update API routes in main app
- [ ] Configure WebSocket server settings
- [ ] Start background scheduler job
- [ ] Test on staging environment

### 10.2 Frontend Deployment

- [ ] Build production bundle
- [ ] Test production build locally
- [ ] Deploy to production
- [ ] Verify all features work in production
- [ ] Monitor error logs for issues

---

## Critical Files Checklist

### Backend (Priority Order)

- [ ] `apps/sqlite/schema.py` - Add simulation tables
- [ ] `apps/sqlite/simulator.py` - Database operations
- [ ] `apps/simulator/session.py` - Simulation session manager (~300 lines)
- [ ] `apps/api/routes/simulator.py` - API endpoints & WebSocket (~200 lines)
- [ ] `apps/scheduler.py` - Background cleanup jobs (~50 lines)

### Frontend (Priority Order)

- [ ] `ui/src/lib/api/simulator.ts` - API client (~100 lines)
- [ ] `ui/src/app/(dashboard)/simulation/page.tsx` - Main page (~100 lines)
- [ ] `ui/src/components/simulation/config-form.tsx` - Config form (~150 lines)
- [ ] `ui/src/components/simulation/execution-view.tsx` - Execution container (~200 lines)
- [ ] `ui/src/components/simulation/simulation-chart.tsx` - Real-time chart (~250 lines)
- [ ] `ui/src/components/simulation/trading-panel.tsx` - Trading controls (~150 lines)
- [ ] `ui/src/components/simulation/speed-control.tsx` - Speed controls (~100 lines)
- [ ] `ui/src/components/simulation/positions-panel.tsx` - Positions list (~100 lines)
- [ ] `ui/src/components/simulation/orders-panel.tsx` - Orders list (~100 lines)
- [ ] `ui/src/components/simulation/account-metrics.tsx` - Metrics bar (~80 lines)
- [ ] `ui/src/components/simulation/trade-dialog.tsx` - Chart-click dialog (~120 lines)
- [ ] `ui/src/components/simulation/results-view.tsx` - Results summary (~150 lines)

**Total Estimated**: ~2200 lines of new code

---

## Session Progress Tracker

### Session 1 (Current)

- [X] Planning phase completed
- [X] User requirements gathered
- [X] Architecture designed
- [X] Checklist created

### Session 2

- [ ] Phase 1: Backend Foundation (Database + Session Manager)

### Session 3

- [ ] Phase 1 continued: API Routes + Background Jobs

### Session 4

- [ ] Phase 2: Frontend Structure (API Client + Main Page + Config Form)

### Session 5

- [ ] Phase 3: Real-Time Chart Component

### Session 6

- [ ] Phase 4: Trading Controls (Speed + Trading Panel + Dialog)

### Session 7

- [ ] Phase 5: Position & Account Management

### Session 8

- [ ] Phase 6: Execution View Container

### Session 9

- [ ] Phase 7: Results View

### Session 10

- [ ] Phase 8-10: Testing, Polish, Documentation, Deployment

---

## Notes & Observations

### Design Decisions

- Using WebSocket for streaming (not REST polling) for lower latency
- Backend controls speed to prevent frontend overwhelm
- In-memory session store (consider Redis for production scale)
- Immediate trade persistence (never lose data)
- Resume capability requires saving current_bar_index to database

### Known Limitations

- X1440 speed may skip visual frames but data stays accurate
- Mobile view simplified (chart-only, trading panel hidden)
- Single user per session assumed (extend with user_id checks for multi-user)

### Future Enhancements

- Multi-symbol simulation (portfolio mode)
- Risk management rules (max drawdown stop, daily loss limit)
- Advanced order types (trailing stop, OCO orders)
- Social features (share simulations, leaderboards)
- AI-assisted trading suggestions during simulation

---

**Last Updated**: 2026-01-27
**Status**: Planning Complete, Ready for Implementation
