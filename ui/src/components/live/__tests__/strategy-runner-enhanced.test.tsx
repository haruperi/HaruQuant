/**
 * Unit Tests for StrategyRunnerEnhanced Component
 *
 * Tests session selection and control functionality
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StrategyRunnerEnhanced } from '../strategy-runner-enhanced'
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

const mockSessions = [
  {
    session_id: 1,
    session_name: 'Paper Trading Session',
    mode: 'paper' as const,
    status: 'stopped' as const,
    max_positions: 5,
    max_total_risk_pct: 2.0,
    max_drawdown_pct: 10.0,
  },
  {
    session_id: 2,
    session_name: 'Live Trading Session',
    mode: 'live' as const,
    status: 'running' as const,
    max_positions: 3,
    max_total_risk_pct: 1.0,
    max_drawdown_pct: 5.0,
  },
]

const mockStatus = {
  session_id: 1,
  session_name: 'Paper Trading Session',
  status: 'stopped' as const,
  running: false,
  paused: false,
  signals_detected: 10,
  signals_approved: 7,
  signals_rejected: 3,
  positions_opened: 5,
  positions_closed: 2,
  active_positions: 0,
}

describe('StrategyRunnerEnhanced', () => {
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

  it('renders loading state while fetching sessions', () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockImplementation(
      () => new Promise(() => {})
    )

    render(<StrategyRunnerEnhanced />)

    expect(screen.getByText('Loading sessions...')).toBeInTheDocument()
  })

  it('renders no sessions message when list is empty', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue([])

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(
        screen.getByText('No sessions available. Create a session to get started.')
      ).toBeInTheDocument()
    })
  })

  it('displays session list successfully', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByText(/Paper Trading Session/i)).toBeInTheDocument()
    })
  })

  it('displays mode badge correctly for paper trading', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByText('PAPER TRADING')).toBeInTheDocument()
    })
  })

  it('displays mode badge correctly for live trading', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[1])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue({
      ...mockStatus,
      session_id: 2,
      status: 'running',
    })

    render(<StrategyRunnerEnhanced sessionId={2} />)

    await waitFor(() => {
      expect(screen.getByText('LIVE TRADING')).toBeInTheDocument()
    })
  })

  it('shows Start button for stopped session', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start session/i })).toBeInTheDocument()
    })
  })

  it('shows Pause and Stop buttons for running session', async () => {
    const runningStatus = { ...mockStatus, status: 'running' as const, running: true }
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(runningStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument()
    })
  })

  it('shows Resume and Stop buttons for paused session', async () => {
    const pausedStatus = { ...mockStatus, status: 'paused' as const, paused: true }
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(pausedStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /resume/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument()
    })
  })

  it('calls startSession API when Start button is clicked', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)
    ;(LiveTradingAPI.startSession as jest.Mock).mockResolvedValue({
      message: 'Session started',
      session_id: 1,
      status: 'starting',
    })

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start session/i })).toBeInTheDocument()
    })

    const startButton = screen.getByRole('button', { name: /start session/i })
    await userEvent.click(startButton)

    await waitFor(() => {
      expect(LiveTradingAPI.startSession).toHaveBeenCalledWith(1)
    })
  })

  it('calls stopSession API when Stop button is clicked', async () => {
    const runningStatus = { ...mockStatus, status: 'running' as const, running: true }
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(runningStatus)
    ;(LiveTradingAPI.stopSession as jest.Mock).mockResolvedValue({
      message: 'Session stopped',
      session_id: 1,
      status: 'stopped',
    })

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument()
    })

    const stopButton = screen.getByRole('button', { name: /stop/i })
    await userEvent.click(stopButton)

    await waitFor(() => {
      expect(LiveTradingAPI.stopSession).toHaveBeenCalledWith(1)
    })
  })

  it('calls pauseSession API when Pause button is clicked', async () => {
    const runningStatus = { ...mockStatus, status: 'running' as const, running: true }
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(runningStatus)
    ;(LiveTradingAPI.pauseSession as jest.Mock).mockResolvedValue({
      message: 'Session paused',
      session_id: 1,
      status: 'paused',
    })

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument()
    })

    const pauseButton = screen.getByRole('button', { name: /pause/i })
    await userEvent.click(pauseButton)

    await waitFor(() => {
      expect(LiveTradingAPI.pauseSession).toHaveBeenCalledWith(1)
    })
  })

  it('calls resumeSession API when Resume button is clicked', async () => {
    const pausedStatus = { ...mockStatus, status: 'paused' as const, paused: true }
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(pausedStatus)
    ;(LiveTradingAPI.resumeSession as jest.Mock).mockResolvedValue({
      message: 'Session resumed',
      session_id: 1,
      status: 'running',
    })

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /resume/i })).toBeInTheDocument()
    })

    const resumeButton = screen.getByRole('button', { name: /resume/i })
    await userEvent.click(resumeButton)

    await waitFor(() => {
      expect(LiveTradingAPI.resumeSession).toHaveBeenCalledWith(1)
    })
  })

  it('disables buttons during action pending', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)
    ;(LiveTradingAPI.startSession as jest.Mock).mockImplementation(
      () => new Promise(() => {})
    )

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start session/i })).toBeInTheDocument()
    })

    const startButton = screen.getByRole('button', { name: /start session/i })
    await userEvent.click(startButton)

    await waitFor(() => {
      expect(startButton).toBeDisabled()
    })
  })

  it('displays session details correctly', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // max_positions
      expect(screen.getByText('2%')).toBeInTheDocument() // max_total_risk_pct
      expect(screen.getByText('10%')).toBeInTheDocument() // max_drawdown_pct
    })
  })

  it('displays performance metrics correctly', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByText('10')).toBeInTheDocument() // signals_detected
      expect(screen.getByText('7')).toBeInTheDocument() // signals_approved
      expect(screen.getByText('3')).toBeInTheDocument() // signals_rejected
    })
  })

  it('calls onSessionChange when session is selected', async () => {
    const onSessionChange = jest.fn()
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced onSessionChange={onSessionChange} />)

    await waitFor(() => {
      expect(onSessionChange).toHaveBeenCalledWith(1)
    })
  })

  it('displays WebSocket connection indicator', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockResolvedValue(mockSessions)
    ;(LiveTradingAPI.getSession as jest.Mock).mockResolvedValue(mockSessions[0])
    ;(LiveTradingAPI.getSessionStatus as jest.Mock).mockResolvedValue(mockStatus)

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument()
    })
  })

  it('displays error state on API failure', async () => {
    ;(LiveTradingAPI.listSessions as jest.Mock).mockRejectedValue(
      new Error('Network error')
    )

    render(<StrategyRunnerEnhanced />)

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })
})
