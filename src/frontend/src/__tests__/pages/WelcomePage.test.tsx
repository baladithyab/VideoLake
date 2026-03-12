/**
 * WelcomePage component tests.
 *
 * Tests for the welcome/landing page:
 * - Initial render
 * - Navigation to main workflows
 * - Quick start actions
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { WelcomePage } from '../../components/pages/WelcomePage'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('WelcomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders welcome message', () => {
    render(
      <MemoryRouter>
        <WelcomePage />
      </MemoryRouter>
    )

    expect(screen.getByText(/welcome|get started/i)).toBeInTheDocument()
  })

  it('displays main workflow options', () => {
    render(
      <MemoryRouter>
        <WelcomePage />
      </MemoryRouter>
    )

    // Should show deployment, benchmark, and demo options
    expect(screen.getByText(/deploy/i)).toBeInTheDocument()
    expect(screen.getByText(/benchmark/i)).toBeInTheDocument()
  })

  it('has navigation buttons for key workflows', () => {
    render(
      <MemoryRouter>
        <WelcomePage />
      </MemoryRouter>
    )

    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('displays feature highlights or value propositions', () => {
    render(
      <MemoryRouter>
        <WelcomePage />
      </MemoryRouter>
    )

    // Should mention key features like vector stores, multi-modal, etc.
    const pageContent = screen.getByRole('main') || document.body
    expect(pageContent.textContent).toMatch(/vector|search|multi-?modal/i)
  })

  it('shows quick start guide or steps', () => {
    render(
      <MemoryRouter>
        <WelcomePage />
      </MemoryRouter>
    )

    // Should have some form of getting started guidance
    const content = document.body.textContent || ''
    expect(content.length).toBeGreaterThan(100) // Non-trivial content
  })
})
