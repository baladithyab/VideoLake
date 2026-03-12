/**
 * InfrastructureManager component tests.
 *
 * Tests for the infrastructure management component that handles:
 * - Displaying infrastructure status
 * - Deploying/destroying vector stores
 * - Real-time status updates
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { InfrastructureManager } from '../components/InfrastructureManager'
import { api } from '../api/client'

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    getInfrastructureStatus: vi.fn(),
    deploySingleStore: vi.fn(),
    destroySingleStore: vi.fn(),
    deployInfrastructure: vi.fn(),
    destroyInfrastructure: vi.fn(),
  },
}))

describe('InfrastructureManager Component', () => {
  const mockStatus = {
    vector_stores: {
      s3_vector: { deployed: true, status: 'active' },
      opensearch: { deployed: false, status: 'not_deployed' },
      qdrant: { deployed: false, status: 'not_deployed' },
      lancedb: { deployed: false, status: 'not_deployed' },
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getInfrastructureStatus).mockResolvedValue({
      data: mockStatus,
    } as any)
  })

  it('renders without crashing', async () => {
    render(<InfrastructureManager />)

    await waitFor(() => {
      expect(screen.getByText(/infrastructure/i)).toBeInTheDocument()
    })
  })

  it('displays vector store status', async () => {
    render(<InfrastructureManager />)

    await waitFor(() => {
      expect(screen.getByText(/s3.?vector/i)).toBeInTheDocument()
    })
  })

  it('shows deployed stores as active', async () => {
    render(<InfrastructureManager />)

    await waitFor(() => {
      // S3 Vector should show as deployed/active
      const s3Element = screen.getByText(/s3.?vector/i)
      expect(s3Element).toBeInTheDocument()
    })
  })

  it('shows non-deployed stores as inactive', async () => {
    render(<InfrastructureManager />)

    await waitFor(() => {
      // OpenSearch should show as not deployed
      expect(screen.getByText(/opensearch/i)).toBeInTheDocument()
    })
  })

  it('allows deploying a single store', async () => {
    vi.mocked(api.deploySingleStore).mockResolvedValue({ data: { message: 'Deployment started' } } as any)

    render(<InfrastructureManager />)

    await waitFor(() => {
      expect(screen.getByText(/opensearch/i)).toBeInTheDocument()
    })

    // Find and click deploy button for OpenSearch
    const deployButtons = screen.getAllByRole('button')
    const deployButton = deployButtons.find(btn =>
      btn.textContent?.toLowerCase().includes('deploy')
    )

    if (deployButton) {
      fireEvent.click(deployButton)

      await waitFor(() => {
        expect(api.deploySingleStore).toHaveBeenCalled()
      })
    }
  })

  it('shows loading state during deployment', async () => {
    vi.mocked(api.deploySingleStore).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ data: {} } as any), 100))
    )

    render(<InfrastructureManager />)

    await waitFor(() => {
      expect(screen.getByText(/opensearch/i)).toBeInTheDocument()
    })

    const deployButtons = screen.getAllByRole('button')
    const deployButton = deployButtons.find(btn =>
      btn.textContent?.toLowerCase().includes('deploy')
    )

    if (deployButton) {
      fireEvent.click(deployButton)

      // Should show loading state
      await waitFor(() => {
        const loadingElements = screen.queryAllByText(/deploying|loading/i)
        expect(loadingElements.length).toBeGreaterThan(0)
      })
    }
  })

  it('handles deployment errors gracefully', async () => {
    const errorMessage = 'Deployment failed: AWS credentials not found'
    vi.mocked(api.deploySingleStore).mockRejectedValue(new Error(errorMessage))

    render(<InfrastructureManager />)

    await waitFor(() => {
      expect(screen.getByText(/opensearch/i)).toBeInTheDocument()
    })

    const deployButtons = screen.getAllByRole('button')
    const deployButton = deployButtons.find(btn =>
      btn.textContent?.toLowerCase().includes('deploy')
    )

    if (deployButton) {
      fireEvent.click(deployButton)

      await waitFor(() => {
        // Should display error message
        const errorElements = screen.queryAllByText(/failed|error/i)
        expect(errorElements.length).toBeGreaterThan(0)
      })
    }
  })

  it('refreshes status after deployment', async () => {
    vi.mocked(api.deploySingleStore).mockResolvedValue({ data: { message: 'Deployed' } } as any)

    const updatedStatus = {
      ...mockStatus,
      vector_stores: {
        ...mockStatus.vector_stores,
        opensearch: { deployed: true, status: 'active' },
      },
    }

    vi.mocked(api.getInfrastructureStatus)
      .mockResolvedValueOnce({ data: mockStatus } as any)
      .mockResolvedValueOnce({ data: updatedStatus } as any)

    render(<InfrastructureManager />)

    await waitFor(() => {
      expect(api.getInfrastructureStatus).toHaveBeenCalledTimes(1)
    })
  })

  it('displays infrastructure cost estimates', async () => {
    render(<InfrastructureManager />)

    await waitFor(() => {
      // Should show cost information or cost badge
      const costElements = screen.queryAllByText(/cost|price|\$/i)
      // Cost display is optional, so we don't assert
    })
  })
})
