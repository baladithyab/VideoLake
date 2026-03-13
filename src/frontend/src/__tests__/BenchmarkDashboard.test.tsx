/**
 * BenchmarkDashboard component tests.
 *
 * Tests for the benchmark dashboard that displays:
 * - Benchmark results and metrics
 * - Performance comparisons
 * - Historical benchmark data
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BenchmarkDashboard } from '../components/BenchmarkDashboard'
import { api } from '../api/client'

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    listBenchmarks: vi.fn(),
    getBenchmarkResults: vi.fn(),
  },
}))

describe('BenchmarkDashboard Component', () => {
  const mockBenchmarks = [
    {
      id: 'bench-1',
      name: 'Text Search Performance',
      status: 'completed',
      created_at: '2024-01-15T10:00:00Z',
      metrics: {
        latency_ms: 45,
        throughput_qps: 100,
        accuracy: 0.95,
      },
    },
    {
      id: 'bench-2',
      name: 'Multi-modal Search',
      status: 'running',
      created_at: '2024-01-15T11:00:00Z',
      metrics: null,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listBenchmarks).mockResolvedValue({
      data: mockBenchmarks,
    } as any)
  })

  it('renders without crashing', async () => {
    render(<BenchmarkDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/benchmark/i)).toBeInTheDocument()
    })
  })

  it('displays list of benchmarks', async () => {
    render(<BenchmarkDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/text search performance/i)).toBeInTheDocument()
      expect(screen.getByText(/multi-modal search/i)).toBeInTheDocument()
    })
  })

  it('shows benchmark status indicators', async () => {
    render(<BenchmarkDashboard />)

    await waitFor(() => {
      // Should show completed and running status
      expect(screen.getByText(/completed/i)).toBeInTheDocument()
      expect(screen.getByText(/running/i)).toBeInTheDocument()
    })
  })

  it('displays benchmark metrics for completed benchmarks', async () => {
    render(<BenchmarkDashboard />)

    await waitFor(() => {
      // Should show latency metric
      const latencyText = screen.queryByText(/45.*ms|latency.*45/i)
      expect(latencyText).toBeInTheDocument()
    })
  })

  it('shows placeholder for running benchmarks', async () => {
    render(<BenchmarkDashboard />)

    await waitFor(() => {
      // Running benchmark should not show metrics yet
      expect(screen.getByText(/running/i)).toBeInTheDocument()
    })
  })

  it('handles empty benchmark list', async () => {
    vi.mocked(api.listBenchmarks).mockResolvedValue({
      data: [],
    } as any)

    render(<BenchmarkDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/no benchmarks|empty/i)).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(api.listBenchmarks).mockRejectedValue(new Error('Network error'))

    render(<BenchmarkDashboard />)

    await waitFor(() => {
      const errorElements = screen.queryAllByText(/error|failed/i)
      expect(errorElements.length).toBeGreaterThan(0)
    })
  })

  it('displays create new benchmark button', async () => {
    render(<BenchmarkDashboard />)

    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      const createButton = buttons.find(btn =>
        btn.textContent?.toLowerCase().includes('new') ||
        btn.textContent?.toLowerCase().includes('create')
      )
      expect(createButton).toBeTruthy()
    })
  })
})
