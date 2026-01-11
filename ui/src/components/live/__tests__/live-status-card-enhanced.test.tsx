/**
 * Unit Tests for LiveStatusCardEnhanced Component
 *
 * Tests real-time status monitoring functionality
 */

import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { LiveStatusCardEnhanced } from '../live-status-card-enhanced'
import { LiveTradingAPI } from '@/lib/api/live'
import { useLiveWebSocket } from '@/lib/hooks/use-live-websocket'

// Mock dependencies
jest.mock('@/lib/api/live')
jest.mock('@/lib/hooks/use-live-websocket')
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}))

const mockSessionStatus = {
  session_id: 1,
  session_name: 'Test Session',
  status: 'running' as const,
  running: true,
  paused: false,
  signals_detected: 10,
  signals_approved: 7,
  signals_rejected: 3,
  positions_opened: 5,
  positions_closed: 2,
  active_positions: 3,
}

describe('LiveStatusCardEnhanced', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    // Mock WebSocket hook
    ;(useLiveWebSocket as jest.Mock).mockReturnValue({
      isConnected: true,
      connect: jest.fn(),
      disconnect: jest.fn(),
      subscribe: jest.fn(),
      reconnectAttempts: 0,
    })
  })

  it('renders loading state initially', () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<LiveStatusCardEnhanced sessionId={1} />)

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders session status successfully', async () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Test Session')).toBeInTheDocument()
    })

    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument() // signals_detected
    expect(screen.getByText('3')).toBeInTheDocument() // active_positions
  })

  it('displays error state on API failure', async () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockRejectedValue(
      new Error('Network error')
    )

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('shows WebSocket connection status', async () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)
    ;(useLiveWebSocket as jest.Mock).mockReturnValue({
      isConnected: true,
      connect: jest.fn(),
      disconnect: jest.fn(),
      subscribe: jest.fn(),
      reconnectAttempts: 0,
    })

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument()
    })
  })

  it('shows disconnected status when WebSocket is not connected', async () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)
    ;(useLiveWebSocket as jest.Mock).mockReturnValue({
      isConnected: false,
      connect: jest.fn(),
      disconnect: jest.fn(),
      subscribe: jest.fn(),
      reconnectAttempts: 2,
    })

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Connecting...')).toBeInTheDocument()
    })
  })

  it('updates status via WebSocket callback', async () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)

    let statusUpdateCallback: ((status: any) => void) | undefined

    ;(useLiveWebSocket as jest.Mock).mockImplementation((options) => {
      statusUpdateCallback = options.onStatusUpdate
      return {
        isConnected: true,
        connect: jest.fn(),
        disconnect: jest.fn(),
        subscribe: jest.fn(),
        reconnectAttempts: 0,
      }
    })

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Test Session')).toBeInTheDocument()
    })

    // Simulate WebSocket status update
    const updatedStatus = {
      ...mockSessionStatus,
      signals_detected: 15,
      active_positions: 5,
    }

    if (statusUpdateCallback) {
      statusUpdateCallback(updatedStatus)
    }

    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
    })
  })

  it('calls onStatusUpdate prop when status changes', async () => {
    const onStatusUpdate = jest.fn()
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)

    render(<LiveStatusCardEnhanced sessionId={1} onStatusUpdate={onStatusUpdate} />)

    await waitFor(() => {
      expect(onStatusUpdate).toHaveBeenCalledWith(mockSessionStatus)
    })
  })

  it('displays correct status badge color for running session', async () => {
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      const badge = screen.getByText('Running')
      expect(badge).toHaveClass('bg-emerald-500/10')
    })
  })

  it('displays correct status badge color for paused session', async () => {
    const pausedStatus = { ...mockSessionStatus, status: 'paused' as const }
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(pausedStatus)

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Paused')).toBeInTheDocument()
    })
  })

  it('displays correct status badge color for stopped session', async () => {
    const stoppedStatus = { ...mockSessionStatus, status: 'stopped' as const, running: false }
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(stoppedStatus)

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(screen.getByText('Stopped')).toBeInTheDocument()
    })
  })

  it('polls for status updates every 30 seconds', async () => {
    jest.useFakeTimers()
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)

    render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(LiveTradingAPI.getSessionStatus).toHaveBeenCalledTimes(1)
    })

    // Fast-forward 30 seconds
    jest.advanceTimersByTime(30000)

    await waitFor(() => {
      expect(LiveTradingAPI.getSessionStatus).toHaveBeenCalledTimes(2)
    })

    jest.useRealTimers()
  })

  it('cleans up interval on unmount', async () => {
    jest.useFakeTimers()
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockSessionStatus)

    const { unmount } = render(<LiveStatusCardEnhanced sessionId={1} />)

    await waitFor(() => {
      expect(LiveTradingAPI.getSessionStatus).toHaveBeenCalledTimes(1)
    })

    unmount()

    // Fast-forward 30 seconds
    jest.advanceTimersByTime(30000)

    // Should not be called again after unmount
    expect(LiveTradingAPI.getSessionStatus).toHaveBeenCalledTimes(1)

    jest.useRealTimers()
  })
})
