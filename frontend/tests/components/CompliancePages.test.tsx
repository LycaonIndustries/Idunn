import { describe, expect, it, mock } from 'bun:test'
import { fireEvent, render, screen } from '@testing-library/react'
import {
  HelpDocsPage,
  PrivacyPage,
  SupportPage,
  TermsPage,
} from '../../src/components/legal/CompliancePages'
import { Footer } from '../../src/components/Footer'

describe('Compliance & Legal Pages', () => {
  it('renders PrivacyPage with zero AI training guarantee and GDPR disclosures', () => {
    const onBack = mock(() => {})
    render(<PrivacyPage onBack={onBack} />)

    expect(screen.getByText(/Privacy Policy/i)).toBeDefined()
    expect(screen.getByText(/Zero AI Training Guarantee/i)).toBeDefined()
    expect(screen.getByText(/Right to Erasure & Portability/i)).toBeDefined()

    fireEvent.click(screen.getByText(/Back to App/i))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('renders TermsPage with allergen and medical disclaimers', () => {
    const onBack = mock(() => {})
    render(<TermsPage onBack={onBack} />)

    expect(screen.getByText(/Terms of Service/i)).toBeDefined()
    expect(screen.getByText(/Medical, Dietary & Allergen Disclaimer/i)).toBeDefined()
    expect(screen.getByText(/Bring Your Own Key \(BYOK\) Responsibility/i)).toBeDefined()
  })

  it('renders HelpDocsPage with receipt ingestion and IFCT guides', () => {
    const onBack = mock(() => {})
    render(<HelpDocsPage onBack={onBack} />)

    expect(screen.getByText(/Help & Documentation/i)).toBeDefined()
    expect(screen.getByText(/1. Receipt Ingestion/i)).toBeDefined()
    expect(screen.getByText(/3. ICMR\/NIN IFCT Macros/i)).toBeDefined()
  })

  it('renders SupportPage with support email and GitHub issue links', () => {
    const onBack = mock(() => {})
    render(<SupportPage onBack={onBack} />)

    expect(screen.getByText(/Customer Support & Feedback/i)).toBeDefined()
    expect(screen.getByText(/Email Support/i)).toBeDefined()
    expect(screen.getByText(/Open Issue/i)).toBeDefined()
  })

  it('renders Footer and dispatches compliance navigation events', () => {
    const onNavigate = mock(() => {})
    render(<Footer onNavigateCompliance={onNavigate} />)

    expect(screen.getByText(/GDPR & DPDP Compliant/i)).toBeDefined()

    fireEvent.click(screen.getByText('Privacy Policy'))
    expect(onNavigate).toHaveBeenCalledWith('privacy')

    fireEvent.click(screen.getByText('Terms of Service'))
    expect(onNavigate).toHaveBeenCalledWith('terms')

    fireEvent.click(screen.getByText('Help & Docs'))
    expect(onNavigate).toHaveBeenCalledWith('docs')

    fireEvent.click(screen.getByText('Support'))
    expect(onNavigate).toHaveBeenCalledWith('support')
  })
})
