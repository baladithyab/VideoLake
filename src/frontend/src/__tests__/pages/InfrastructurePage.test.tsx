/**
 * InfrastructurePage component tests.
 *
 * Tests for the infrastructure management page:
 * - Status overview
 * - Deployment controls
 * - Cost tracking
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { InfrastructurePage } from '../../components/pages/InfrastructurePage'
import { api } from '../../api/client'

// Mock API
vi.mock('../../api/client', () => ({
  api: {
    getInfrastructureStatus: vi.fn(),
  },
}))

describe('InfrastructurePage', () => {
  const mockStatus = {
    vector_stores: {
      s3_vector: {
        deployed: true,
        status: 'active',
        endpoint: 'https://s3-vector.example.com',
      },
      opensearch: {
        deployed: false,
        status: 'not_deployed',
      },
      qdrant: {
        deployed: false,
        status: 'not_deployed',
      },
      lancedb: {
        deployed: true,
        status: 'active',
        endpoint: 'https://lancedb.example.com',
      },
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getInfrastructureStatus).mockResolvedValue({
      data: mockStatus,
    } as any)
  })

  it('renders infrastructure page title', async () => {
    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/infrastructure/i)).toBeInTheDocument()
    })
  })

  it('displays vector store status overview', async () => {
    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/s3.?vector/i)).toBeInTheDocument()
      expect(screen.getByText(/opensearch/i)).toBeInTheDocument()
      expect(screen.getByText(/qdrant/i)).toBeInTheDocument()
      expect(screen.getByText(/lancedb/i)).toBeInTheDocument()
    })
  })

  it('shows deployed stores as active', async () => {
    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      // Should show active/deployed indicators
      const activeElements = screen.getAllByText(/active|deployed/i)
      expect(activeElements.length).toBeGreaterThan(0)
    })
  })

  it('shows non-deployed stores appropriately', async () => {
    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      // Should show not deployed status
      const notDeployedElements = screen.getAllByText(/not.?deployed|inactive/i)
      expect(notDeployedElements.length).toBeGreaterThan(0)
    })
  })

  it('has deployment wizard link or button', async () => {
    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const deployButtons = screen.getAllByRole('button')
      const deployAction = deployButtons.find(btn =>
        btn.textContent?.toLowerCase().includes('deploy')
      )
      expect(deployAction).toBeTruthy()
    })
  })

  it('displays infrastructure metrics or stats', async () => {
    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      // Should show some form of metrics (deployed count, costs, etc.)
      const content = document.body.textContent || ''
      expect(content.length).toBeGreaterThan(50)
    })
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(api.getInfrastructureStatus).mockRejectedValue(
      new Error('Failed to fetch status')
    )

    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const errorElements = screen.queryAllByText(/error|failed/i)
      expect(errorElements.length).toBeGreaterThan(0)
    })
  })

  it('shows loading state while fetching status', async () => {
    vi.mocked(api.getInfrastructureStatus).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ data: mockStatus } as any), 100))
    )

    render(
      <MemoryRouter>
        <InfrastructurePage />
      </MemoryRouter>
    )

    // Should show loading indicator
    const loadingElements = screen.queryAllByText(/loading/i)
    expect(loadingElements.length).toBeGreaterThan(0)
  })
})
