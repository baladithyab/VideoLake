/**
 * StatusIndicator component tests.
 *
 * Tests for the status indicator molecule:
 * - Different status states
 * - Color coding
 * - Text display
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusIndicator } from '../../components/molecules/StatusIndicator'

describe('StatusIndicator Component', () => {
  it('renders with active status', () => {
    render(<StatusIndicator status="active" />)

    expect(screen.getByText(/active/i)).toBeInTheDocument()
  })

  it('renders with pending status', () => {
    render(<StatusIndicator status="pending" />)

    expect(screen.getByText(/pending/i)).toBeInTheDocument()
  })

  it('renders with error status', () => {
    render(<StatusIndicator status="error" />)

    expect(screen.getByText(/error/i)).toBeInTheDocument()
  })

  it('renders with inactive status', () => {
    render(<StatusIndicator status="inactive" />)

    expect(screen.getByText(/inactive/i)).toBeInTheDocument()
  })

  it('displays custom label when provided', () => {
    render(<StatusIndicator status="active" label="Running" />)

    expect(screen.getByText(/running/i)).toBeInTheDocument()
  })

  it('applies correct CSS classes for status', () => {
    const { container } = render(<StatusIndicator status="active" />)

    // Should have some indicator element with status-related class
    const indicator = container.querySelector('[class*="status"]')
    expect(indicator).toBeTruthy()
  })
})
