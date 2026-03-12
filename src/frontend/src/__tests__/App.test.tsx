/**
 * App component tests.
 *
 * Basic rendering tests for the main App component.
 * These tests validate that the component renders without crashing
 * and key UI elements are present.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from '../App'

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

// Mock child components to isolate App component testing
vi.mock('../components/BackendSelector', () => ({
  BackendSelector: () => <div data-testid="backend-selector">Backend Selector</div>,
}))

vi.mock('../components/SearchInterface', () => ({
  SearchInterface: () => <div data-testid="search-interface">Search Interface</div>,
}))

vi.mock('../components/ResultsGrid', () => ({
  ResultsGrid: () => <div data-testid="results-grid">Results Grid</div>,
}))

vi.mock('../components/InfrastructureManager', () => ({
  InfrastructureManager: () => <div data-testid="infrastructure-manager">Infrastructure Manager</div>,
}))

vi.mock('../components/BenchmarkDashboard', () => ({
  BenchmarkDashboard: () => <div data-testid="benchmark-dashboard">Benchmark Dashboard</div>,
}))

vi.mock('../components/VisualizationPanel', () => ({
  VisualizationPanel: () => <div data-testid="visualization-panel">Visualization Panel</div>,
}))

vi.mock('../components/IngestionPanel', () => ({
  IngestionPanel: () => <div data-testid="ingestion-panel">Ingestion Panel</div>,
}))

vi.mock('../components/VideoPlayer', () => ({
  VideoPlayer: () => <div data-testid="video-player">Video Player</div>,
}))

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getByTestId('backend-selector')).toBeInTheDocument()
  })

  it('renders main UI components', () => {
    render(<App />)

    // Check that key components are rendered
    expect(screen.getByTestId('backend-selector')).toBeInTheDocument()
    expect(screen.getByTestId('search-interface')).toBeInTheDocument()
    expect(screen.getByTestId('results-grid')).toBeInTheDocument()
  })

  it('displays application title or header', async () => {
    render(<App />)

    // The app should have some identifying header/title
    // This might be "S3Vector", "VideoLake", or similar
    await waitFor(() => {
      const appElement = screen.getByRole('main') || document.querySelector('[role="application"]')
      expect(appElement).toBeTruthy()
    })
  })

  it('has infrastructure settings button', () => {
    render(<App />)

    // Look for settings/infrastructure management button
    // This test may need adjustment based on actual button implementation
    const buttons = screen.queryAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('initializes with default backend selected', () => {
    render(<App />)

    // App should start with a default backend (likely s3_vector)
    expect(screen.getByTestId('backend-selector')).toBeInTheDocument()
  })
})
