/**
 * BenchmarkHubPage component tests.
 *
 * Tests for the benchmark hub landing page:
 * - Benchmark list display
 * - Create new benchmark action
 * - Navigation to benchmark workflows
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { BenchmarkHubPage } from '../../components/pages/BenchmarkHubPage'
import { api } from '../../api/client'

// Mock API
vi.mock('../../api/client', () => ({
  api: {
    listBenchmarks: vi.fn(),
  },
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('BenchmarkHubPage', () => {
  const mockBenchmarks = [
    {
      id: 'bench-1',
      name: 'Text Search Benchmark',
      status: 'completed',
      created_at: '2024-01-15T10:00:00Z',
    },
    {
      id: 'bench-2',
      name: 'Image Search Benchmark',
      status: 'running',
      created_at: '2024-01-15T11:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listBenchmarks).mockResolvedValue({
      data: mockBenchmarks,
    } as any)
  })

  it('renders benchmark hub title', async () => {
    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/benchmark/i)).toBeInTheDocument()
    })
  })

  it('displays list of existing benchmarks', async () => {
    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/text search benchmark/i)).toBeInTheDocument()
      expect(screen.getByText(/image search benchmark/i)).toBeInTheDocument()
    })
  })

  it('shows benchmark status for each entry', async () => {
    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/completed/i)).toBeInTheDocument()
      expect(screen.getByText(/running/i)).toBeInTheDocument()
    })
  })

  it('has create new benchmark button', async () => {
    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      const createButton = buttons.find(btn =>
        btn.textContent?.toLowerCase().includes('new') ||
        btn.textContent?.toLowerCase().includes('create')
      )
      expect(createButton).toBeTruthy()
    })
  })

  it('handles empty benchmark list', async () => {
    vi.mocked(api.listBenchmarks).mockResolvedValue({
      data: [],
    } as any)

    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/no benchmarks|empty|get started/i)).toBeInTheDocument()
    })
  })

  it('displays benchmark history link', async () => {
    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const historyLink = screen.queryByText(/history|view all/i)
      expect(historyLink).toBeInTheDocument()
    })
  })

  it('shows loading state while fetching benchmarks', async () => {
    vi.mocked(api.listBenchmarks).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ data: [] } as any), 100))
    )

    render(
      <MemoryRouter>
        <BenchmarkHubPage />
      </MemoryRouter>
    )

    // Should show loading indicator
    const loadingElements = screen.queryAllByText(/loading/i)
    expect(loadingElements.length).toBeGreaterThan(0)
  })
})
