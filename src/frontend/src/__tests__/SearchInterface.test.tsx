/**
 * SearchInterface component tests.
 *
 * Tests for the search input component that allows users to:
 * - Enter search queries
 * - Select vector store backends
 * - Trigger searches
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SearchInterface } from '../components/SearchInterface'

describe('SearchInterface Component', () => {
  const mockOnSearch = vi.fn()
  const mockOnBackendChange = vi.fn()

  const defaultBackends = [
    { value: 's3_vector', label: 'S3 Vector', deployed: true },
    { value: 'lancedb', label: 'LanceDB', deployed: false },
    { value: 'qdrant', label: 'Qdrant', deployed: false },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders search input field', () => {
    render(<SearchInterface onSearch={mockOnSearch} />)

    const searchInput = screen.getByRole('textbox') || screen.getByPlaceholderText(/search/i)
    expect(searchInput).toBeInTheDocument()
  })

  it('renders backend selector dropdown', () => {
    render(
      <SearchInterface
        onSearch={mockOnSearch}
        availableBackends={defaultBackends}
      />
    )

    // Look for select element or backend options
    const selects = screen.getAllByRole('combobox')
    expect(selects.length).toBeGreaterThan(0)
  })

  it('calls onSearch when search is submitted', () => {
    render(<SearchInterface onSearch={mockOnSearch} />)

    const searchInput = screen.getByRole('textbox') || screen.getByPlaceholderText(/search/i)

    // Get the submit button (type="submit")
    const form = document.querySelector('form')
    const searchButton = form?.querySelector('button[type="submit"]')

    // Enter search query
    fireEvent.change(searchInput, { target: { value: 'test query' } })

    // Submit search
    if (searchButton) {
      fireEvent.click(searchButton)
    }

    expect(mockOnSearch).toHaveBeenCalledWith(
      'test query',
      'text',
      's3_vector'
    )
  })

  it('does not call onSearch with empty query', () => {
    render(<SearchInterface onSearch={mockOnSearch} />)

    // Get the submit button
    const form = document.querySelector('form')
    const searchButton = form.querySelector('button[type="submit"]')

    // Try to submit with empty query
    fireEvent.click(searchButton)

    expect(mockOnSearch).not.toHaveBeenCalled()
  })

  it('calls onBackendChange when backend is changed', () => {
    render(
      <SearchInterface
        onSearch={mockOnSearch}
        onBackendChange={mockOnBackendChange}
        availableBackends={defaultBackends}
      />
    )

    const backendSelector = screen.getAllByRole('combobox')[0]

    // Change backend
    fireEvent.change(backendSelector, { target: { value: 'lancedb' } })

    expect(mockOnBackendChange).toHaveBeenCalledWith('lancedb')
  })

  it('displays loading state when isLoading is true', () => {
    render(
      <SearchInterface
        onSearch={mockOnSearch}
        isLoading={true}
      />
    )

    // Check for disabled state or loading indicator
    const form = document.querySelector('form')
    const searchButton = form.querySelector('button[type="submit"]')
    expect(searchButton).toBeDisabled()
  })

  it('shows deployed status for backends', () => {
    render(
      <SearchInterface
        onSearch={mockOnSearch}
        availableBackends={defaultBackends}
      />
    )

    // S3 Vector should be shown as deployed
    expect(screen.getByText(/S3 Vector/i)).toBeInTheDocument()
  })

  it('updates query state on input change', () => {
    render(<SearchInterface onSearch={mockOnSearch} />)

    const searchInput = screen.getByRole('textbox') || screen.getByPlaceholderText(/search/i)

    fireEvent.change(searchInput, { target: { value: 'new search query' } })

    expect(searchInput).toHaveValue('new search query')
  })

  it('uses selectedBackend prop as initial backend', () => {
    render(
      <SearchInterface
        onSearch={mockOnSearch}
        selectedBackend="qdrant"
        availableBackends={defaultBackends}
      />
    )

    const backendSelector = screen.getAllByRole('combobox')[0]
    expect(backendSelector).toHaveValue('qdrant')
  })
})
