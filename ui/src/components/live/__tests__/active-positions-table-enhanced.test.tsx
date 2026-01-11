/**
 * Unit Tests for ActivePositionsTableEnhanced Component
 *
 * Tests position monitoring and manual trading functionality
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ActivePositionsTableEnhanced } from '../active-positions-table-enhanced'
import { LiveTradingAPI } from '@/lib/api/live'
import { useLiveWebSocket } from '@/lib/hooks/use-live-websocket'

// Mock dependencies
jest.mock('@/lib/api/live')
jest.mock('@/lib/hooks/use-live-websocket')
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}))

const mockPositions = [
  {
    position_id: 1,
    session_id: 1,
    signal_id: 10,
    mt5_ticket: 12345,
    symbol: 'EURUSD',
    type: 'buy' as const,
    open_time: '2025-12-29T10:00:00',
    open_price: 1.0500,
    position_size: 1.0,
    current_price: 1.0520,
    current_profit: 200.0,
    current_profit_pct: 1.9,
    initial_stop_loss: 1.0480,
    current_stop_loss: 1.0480,
    initial_take_profit: 1.0550,
    current_take_profit: 1.0550,
    breakeven_activated: false,
    trailing_stop_activated: false,
    partial_close_count: 0,
    status: 'open' as const,
    close_reason: null,
    close_time: null,
    close_price: null,
    final_profit: null,
    final_profit_pct: null,
    created_at: '2025-12-29T10:00:00',
    updated_at: '2025-12-29T10:30:00',
  },
  {
    position_id: 2,
    session_id: 1,
    signal_id: 11,
    mt5_ticket: 12346,
    symbol: 'XAUUSD',
    type: 'sell' as const,
    open_time: '2025-12-29T11:00:00',
    open_price: 2040.50,
    position_size: 0.5,
    current_price: 2035.00,
    current_profit: 275.0,
    current_profit_pct: 2.7,
    initial_stop_loss: 2050.00,
    current_stop_loss: 2050.00,
    initial_take_profit: 2020.00,
    current_take_profit: 2020.00,
    breakeven_activated: false,
    trailing_stop_activated: false,
    partial_close_count: 0,
    status: 'open' as const,
    close_reason: null,
    close_time: null,
    close_price: null,
    final_profit: null,
    final_profit_pct: null,
    created_at: '2025-12-29T11:00:00',
    updated_at: '2025-12-29T11:30:00',
  },
]

describe('ActivePositionsTableEnhanced', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    ;(useLiveWebSocket as jest.Mock).mockReturnValue({
      isConnected: true,
      connect: jest.fn(),
      disconnect: jest.fn(),
      subscribe: jest.fn(),
      reconnectAttempts: 0,
    })
  })

  it('renders loading state initially', () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockImplementation(
      () => new Promise(() => {})
    )

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    expect(screen.getByText('Loading positions...')).toBeInTheDocument()
  })

  it('displays positions successfully', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
      expect(screen.getByText('XAUUSD')).toBeInTheDocument()
    })

    expect(screen.getByText('2')).toBeInTheDocument() // badge count
  })

  it('displays empty state when no positions', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue([])

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('No active positions')).toBeInTheDocument()
    })
  })

  it('displays error state on API failure', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockRejectedValue(
      new Error('Network error')
    )

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('displays position details correctly', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      // Check symbol
      expect(screen.getByText('EURUSD')).toBeInTheDocument()

      // Check type
      expect(screen.getByText('BUY')).toBeInTheDocument()

      // Check size
      expect(screen.getByText('1.00')).toBeInTheDocument()

      // Check prices
      expect(screen.getByText('1.05000')).toBeInTheDocument()
      expect(screen.getByText('1.05200')).toBeInTheDocument()

      // Check SL/TP
      expect(screen.getByText('1.04800')).toBeInTheDocument()
      expect(screen.getByText('1.05500')).toBeInTheDocument()

      // Check profit
      expect(screen.getByText('+200.00')).toBeInTheDocument()
      expect(screen.getByText('(+1.90%)')).toBeInTheDocument()
    })
  })

  it('displays negative profit in red', async () => {
    const losingPosition = {
      ...mockPositions[0],
      current_profit: -100.0,
      current_profit_pct: -0.95,
    }
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue([losingPosition])

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      const profitElement = screen.getByText('-100.00')
      expect(profitElement).toHaveClass('text-red-500')
    })
  })

  it('opens modify dialog when Edit button is clicked', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
    })

    // Find all edit buttons and click the first one
    const editButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('svg') // Has icon
    )[0]

    await userEvent.click(editButtons)

    await waitFor(() => {
      expect(screen.getByText('Modify Position')).toBeInTheDocument()
      expect(screen.getByLabelText('Stop Loss')).toBeInTheDocument()
      expect(screen.getByLabelText('Take Profit')).toBeInTheDocument()
    })
  })

  it('calls modifyPosition API when modify dialog is submitted', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)
    ;(LiveTradingAPI.modifyPosition as jest.Mock).mockResolvedValue({
      message: 'Position modified',
      position_id: 1,
      stop_loss: 1.0490,
      take_profit: 1.0560,
    })

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
    })

    // Open modify dialog
    const editButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('svg')
    )[0]
    await userEvent.click(editButtons)

    await waitFor(() => {
      expect(screen.getByLabelText('Stop Loss')).toBeInTheDocument()
    })

    // Change SL and TP
    const slInput = screen.getByLabelText('Stop Loss')
    const tpInput = screen.getByLabelText('Take Profit')

    await userEvent.clear(slInput)
    await userEvent.type(slInput, '1.0490')

    await userEvent.clear(tpInput)
    await userEvent.type(tpInput, '1.0560')

    // Submit
    const updateButton = screen.getByRole('button', { name: /update/i })
    await userEvent.click(updateButton)

    await waitFor(() => {
      expect(LiveTradingAPI.modifyPosition).toHaveBeenCalledWith(1, 1, {
        stop_loss: 1.049,
        take_profit: 1.056,
      })
    })
  })

  it('opens close dialog when Close button is clicked', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
    })

    // Find all close buttons (with XCircle icon) and click the first one
    const closeButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('svg')
    )[1] // Second icon button is close

    await userEvent.click(closeButtons)

    await waitFor(() => {
      expect(screen.getByText('Close Position')).toBeInTheDocument()
      expect(
        screen.getByText('Are you sure you want to close this position?')
      ).toBeInTheDocument()
    })
  })

  it('calls closePosition API when close dialog is confirmed', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)
    ;(LiveTradingAPI.closePosition as jest.Mock).mockResolvedValue({
      message: 'Position closed',
      position_id: 1,
      reason: 'manual_close',
    })

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
    })

    // Open close dialog
    const closeButtons = screen.getAllByRole('button', { name: '' }).filter(
      (btn) => btn.querySelector('svg')
    )[1]
    await userEvent.click(closeButtons)

    await waitFor(() => {
      expect(screen.getByText('Close Position')).toBeInTheDocument()
    })

    // Confirm close
    const confirmButton = screen.getByRole('button', { name: /close position/i })
    await userEvent.click(confirmButton)

    await waitFor(() => {
      expect(LiveTradingAPI.closePosition).toHaveBeenCalledWith(1, 1)
    })
  })

  it('updates position via WebSocket onPositionUpdated callback', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    let positionUpdatedCallback: ((position: any) => void) | undefined

    ;(useLiveWebSocket as jest.Mock).mockImplementation((options) => {
      positionUpdatedCallback = options.onPositionUpdated
      return {
        isConnected: true,
        connect: jest.fn(),
        disconnect: jest.fn(),
        subscribe: jest.fn(),
        reconnectAttempts: 0,
      }
    })

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('+200.00')).toBeInTheDocument()
    })

    // Simulate WebSocket position update
    const updatedPosition = {
      ...mockPositions[0],
      current_price: 1.0530,
      current_profit: 300.0,
      current_profit_pct: 2.86,
    }

    if (positionUpdatedCallback) {
      positionUpdatedCallback(updatedPosition)
    }

    await waitFor(() => {
      expect(screen.getByText('+300.00')).toBeInTheDocument()
      expect(screen.getByText('(+2.86%)')).toBeInTheDocument()
    })
  })

  it('adds new position via WebSocket onPositionOpened callback', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue([mockPositions[0]])

    let positionOpenedCallback: ((position: any) => void) | undefined

    ;(useLiveWebSocket as jest.Mock).mockImplementation((options) => {
      positionOpenedCallback = options.onPositionOpened
      return {
        isConnected: true,
        connect: jest.fn(),
        disconnect: jest.fn(),
        subscribe: jest.fn(),
        reconnectAttempts: 0,
      }
    })

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
      expect(screen.queryByText('XAUUSD')).not.toBeInTheDocument()
    })

    // Simulate WebSocket new position
    if (positionOpenedCallback) {
      positionOpenedCallback(mockPositions[1])
    }

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
      expect(screen.getByText('XAUUSD')).toBeInTheDocument()
    })
  })

  it('removes position via WebSocket onPositionClosed callback', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    let positionClosedCallback: ((position: any, reason: string) => void) | undefined

    ;(useLiveWebSocket as jest.Mock).mockImplementation((options) => {
      positionClosedCallback = options.onPositionClosed
      return {
        isConnected: true,
        connect: jest.fn(),
        disconnect: jest.fn(),
        subscribe: jest.fn(),
        reconnectAttempts: 0,
      }
    })

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('EURUSD')).toBeInTheDocument()
      expect(screen.getByText('XAUUSD')).toBeInTheDocument()
    })

    // Simulate WebSocket position close
    if (positionClosedCallback) {
      positionClosedCallback(mockPositions[0], 'take_profit')
    }

    await waitFor(() => {
      expect(screen.queryByText('EURUSD')).not.toBeInTheDocument()
      expect(screen.getByText('XAUUSD')).toBeInTheDocument()
    })
  })

  it('displays WebSocket connection indicator', async () => {
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      // Check for the green connection dot (using bg-emerald-500 class)
      const connectionDot = document.querySelector('.bg-emerald-500')
      expect(connectionDot).toBeInTheDocument()
    })
  })

  it('polls for position updates every 30 seconds', async () => {
    jest.useFakeTimers()
    ;(LiveTradingAPI.getPositions as jest.Mock).mockResolvedValue(mockPositions)

    render(<ActivePositionsTableEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(LiveTradingAPI.getPositions).toHaveBeenCalledTimes(1)
    })

    // Fast-forward 30 seconds
    jest.advanceTimersByTime(30000)

    await waitFor(() => {
      expect(LiveTradingAPI.getPositions).toHaveBeenCalledTimes(2)
    })

    jest.useRealTimers()
  })
})
