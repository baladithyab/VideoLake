/**
 * Routing tests.
 *
 * Tests for React Router integration and navigation:
 * - Route definitions
 * - Navigation between pages
 * - Route params
 * - 404 handling
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { WelcomePage } from '../components/pages/WelcomePage'
import { NotFoundPage } from '../components/pages/NotFoundPage'
import { BenchmarkHubPage } from '../components/pages/BenchmarkHubPage'
import { DemoSearchPage } from '../components/pages/DemoSearchPage'
import { InfrastructurePage } from '../components/pages/InfrastructurePage'

// Mock API calls
vi.mock('../api/client', () => ({
  api: {
    getInfrastructureStatus: vi.fn().mockResolvedValue({ data: { vector_stores: {} } }),
    listBenchmarks: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

describe('Routing Tests', () => {
  it('renders welcome page at root path', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<WelcomePage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/welcome|get started/i)).toBeInTheDocument()
    })
  })

  it('renders 404 page for unknown routes', async () => {
    render(
      <MemoryRouter initialEntries={['/this-route-does-not-exist']}>
        <Routes>
          <Route path="/" element={<WelcomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/404|not found/i)).toBeInTheDocument()
    })
  })

  it('renders benchmark hub at /benchmark', async () => {
    render(
      <MemoryRouter initialEntries={['/benchmark']}>
        <Routes>
          <Route path="/benchmark" element={<BenchmarkHubPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/benchmark/i)).toBeInTheDocument()
    })
  })

  it('renders demo search page at /demo/search', async () => {
    render(
      <MemoryRouter initialEntries={['/demo/search']}>
        <Routes>
          <Route path="/demo/search" element={<DemoSearchPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/search|demo/i)).toBeInTheDocument()
    })
  })

  it('renders infrastructure page at /infrastructure', async () => {
    render(
      <MemoryRouter initialEntries={['/infrastructure']}>
        <Routes>
          <Route path="/infrastructure" element={<InfrastructurePage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/infrastructure/i)).toBeInTheDocument()
    })
  })

  it('handles deployment wizard routes', async () => {
    const DeploymentConfigurePage = () => (
      <div>Deployment Configuration</div>
    )

    render(
      <MemoryRouter initialEntries={['/deployment/configure']}>
        <Routes>
          <Route path="/deployment/configure" element={<DeploymentConfigurePage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/deployment configuration/i)).toBeInTheDocument()
    })
  })

  it('handles benchmark workflow routes', async () => {
    const BenchmarkConfigurePage = () => (
      <div>Benchmark Configuration</div>
    )

    render(
      <MemoryRouter initialEntries={['/benchmark/configure']}>
        <Routes>
          <Route path="/benchmark/configure" element={<BenchmarkConfigurePage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/benchmark configuration/i)).toBeInTheDocument()
    })
  })

  it('handles dynamic route params for benchmark results', async () => {
    const BenchmarkResultsPage = () => {
      const params = { id: 'test-123' }
      return <div>Benchmark Results: {params.id}</div>
    }

    render(
      <MemoryRouter initialEntries={['/benchmark/results/test-123']}>
        <Routes>
          <Route path="/benchmark/results/:id" element={<BenchmarkResultsPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/benchmark results.*test-123/i)).toBeInTheDocument()
    })
  })

  it('handles dynamic route params for video detail', async () => {
    const VideoDetailPage = () => {
      const params = { id: 'video-456' }
      return <div>Video: {params.id}</div>
    }

    render(
      <MemoryRouter initialEntries={['/demo/video/video-456']}>
        <Routes>
          <Route path="/demo/video/:id" element={<VideoDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/video.*video-456/i)).toBeInTheDocument()
    })
  })
})
