import { AlertTriangle, BookOpen, ExternalLink, HelpCircle, Mail, Shield, Sparkles } from 'lucide-react'

interface LegalPageProps {
  onBack: () => void
}

export function PrivacyPage({ onBack }: LegalPageProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Shield className="w-6 h-6 text-emerald-400" />
            Privacy Policy
          </h1>
          <p className="text-xs text-slate-400">Compliant with GDPR Article 13/14 & India DPDP Act 2023</p>
        </div>
        <button
          onClick={onBack}
          className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white cursor-pointer"
        >
          &larr; Back to App
        </button>
      </div>

      <div className="space-y-4 text-sm text-slate-300 leading-relaxed">
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h2 className="text-base font-semibold text-slate-200">1. Zero AI Training Guarantee</h2>
          <p>
            Iðunn enforces a strict zero-training policy. Your recipe notes, grocery receipts, pantry photos, and dietary preferences
            are processed ephemerally via private enterprise API endpoints and are <strong>NEVER used to train or fine-tune third-party AI models</strong>.
          </p>
        </section>

        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h2 className="text-base font-semibold text-slate-200">2. Personal Data Collected</h2>
          <ul className="list-disc list-inside space-y-1 text-slate-400">
            <li><strong>Pantry Items:</strong> Ingredient names, quantities, and expiration dates.</li>
            <li><strong>Grocery Receipts:</strong> Scanned store names, itemized prices, and purchase dates.</li>
            <li><strong>Recipe Vault:</strong> Saved cooking instructions and dietary tags.</li>
            <li><strong>BYOK Credentials:</strong> API keys stored locally in runtime memory and encrypted environment files.</li>
          </ul>
        </section>

        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h2 className="text-base font-semibold text-slate-200">3. Right to Erasure & Portability</h2>
          <p>
            Under GDPR Article 17 and DPDP Section 12, you hold the right to complete erasure. Navigating to
            Settings &gt; Data Privacy enables 1-click machine-readable JSON archive export or permanent account erasure.
          </p>
        </section>
      </div>
    </div>
  )
}

export function TermsPage({ onBack }: LegalPageProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
            Terms of Service & Allergen Disclaimer
          </h1>
          <p className="text-xs text-slate-400">Please read carefully before using Cook AI & recipe tools</p>
        </div>
        <button
          onClick={onBack}
          className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white cursor-pointer"
        >
          &larr; Back to App
        </button>
      </div>

      <div className="space-y-4 text-sm text-slate-300 leading-relaxed">
        <section className="bg-amber-950/20 border border-amber-500/30 rounded-2xl p-5 space-y-2">
          <h2 className="text-base font-semibold text-amber-300">1. Medical, Dietary & Allergen Disclaimer</h2>
          <p>
            Nutritional metrics (including IFCT compositional tables) and Cook AI ingredient substitutions are provided strictly for
            informational purposes. <strong>Users must independently verify all ingredients for food allergies, cross-contamination, and spoilage.</strong> Iðunn does not replace certified dietary or medical counsel.
          </p>
        </section>

        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h2 className="text-base font-semibold text-slate-200">2. Bring Your Own Key (BYOK) Responsibility</h2>
          <p>
            When using custom Gemini, Anthropic, or OpenAI API keys, users are solely responsible for maintaining key confidentiality
            and any usage costs incurred with third-party foundation model providers.
          </p>
        </section>

        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h2 className="text-base font-semibold text-slate-200">3. Software License</h2>
          <p>
            Iðunn Kitchen OS is licensed under the Lycaon Source-Available License for AI (LSAL-AI 1.0). Commercial cloud hosting or resale requires explicit authorization.
          </p>
        </section>
      </div>
    </div>
  )
}

export function HelpDocsPage({ onBack }: LegalPageProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-sky-400" />
            Help & Documentation
          </h1>
          <p className="text-xs text-slate-400">User guide for smart kitchen inventory and meal planning</p>
        </div>
        <button
          onClick={onBack}
          className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white cursor-pointer"
        >
          &larr; Back to App
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-300">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h3 className="font-semibold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-orange-400" />
            1. Receipt Ingestion
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Upload images from Blinkit, Zepto, or Instamart. Vision OCR automatically extracts purchased grocery items, assigns shelf-life estimates, and adds items to your pantry stock.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h3 className="font-semibold text-slate-100 flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-emerald-400" />
            2. FEFO Pantry Tracking
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            First-Expired, First-Out (FEFO) logic monitors shelf-life. Expiring items are ranked highest in Cook AI suggestions to prevent kitchen food waste.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h3 className="font-semibold text-slate-100 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-sky-400" />
            3. ICMR/NIN IFCT Macros
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Recipes automatically calculate calories, protein, carbs, fat, and fiber using National Institute of Nutrition Indian Food Composition Tables (IFCT 2017).
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
          <h3 className="font-semibold text-slate-100 flex items-center gap-2">
            <Shield className="w-4 h-4 text-purple-400" />
            4. Hands-Free Cooking
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Activate hands-free mode in recipe detail view. Cover or wave across your front camera to advance steps without touching your device with messy kitchen hands.
          </p>
        </div>
      </div>
    </div>
  )
}

export function SupportPage({ onBack }: LegalPageProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Mail className="w-6 h-6 text-orange-400" />
            Customer Support & Feedback
          </h1>
          <p className="text-xs text-slate-400">Get assistance or report issues to the engineering team</p>
        </div>
        <button
          onClick={onBack}
          className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white cursor-pointer"
        >
          &larr; Back to App
        </button>
      </div>

      <div className="space-y-4 text-sm text-slate-300">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-100">Direct Support Inquiries</h3>
            <p className="text-xs text-slate-400">Average response time within 24 business hours.</p>
          </div>
          <a
            href="mailto:support@lycaon.kitchen"
            className="px-4 py-2 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-xs font-semibold transition"
          >
            Email Support
          </a>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-100">GitHub Issue Tracker</h3>
            <p className="text-xs text-slate-400">Report bugs, submit feature requests, or view active roadmap.</p>
          </div>
          <a
            href="https://github.com/LycaonIndustries/Idunn/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition"
          >
            <span>Open Issue</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  )
}
