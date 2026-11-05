import { ExternalLink, ShieldCheck } from 'lucide-react'

export type ComplianceTab = 'privacy' | 'terms' | 'docs' | 'support'

interface FooterProps {
  onNavigateCompliance: (tab: ComplianceTab) => void
}

/**
 * Universal application footer with legal compliance and support links.
 */
export function Footer({ onNavigateCompliance }: FooterProps) {
  return (
    <footer className="py-8 border-t border-slate-900 bg-slate-950 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span>Iðunn Kitchen OS • GDPR &amp; DPDP Compliant • Zero AI Training</span>
        </div>

        <nav aria-label="Footer Navigation" className="flex flex-wrap items-center gap-4 text-slate-400">
          <button
            type="button"
            onClick={() => onNavigateCompliance('privacy')}
            className="hover:text-slate-200 transition cursor-pointer"
          >
            Privacy Policy
          </button>
          <button
            type="button"
            onClick={() => onNavigateCompliance('terms')}
            className="hover:text-slate-200 transition cursor-pointer"
          >
            Terms of Service
          </button>
          <button
            type="button"
            onClick={() => onNavigateCompliance('docs')}
            className="hover:text-slate-200 transition cursor-pointer"
          >
            Help &amp; Docs
          </button>
          <button
            type="button"
            onClick={() => onNavigateCompliance('support')}
            className="hover:text-slate-200 transition cursor-pointer"
          >
            Support
          </button>
          <a
            href="https://github.com/LycaonIndustries/Idunn"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 hover:text-slate-200 transition"
          >
            <span>GitHub</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </nav>
      </div>
    </footer>
  )
}
