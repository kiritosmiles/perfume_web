import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export function PrivacyPage() {
  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center">
          <Link to="/" className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Home
          </Link>
          <span className="ml-auto text-sm font-medium text-stone-700">Privacy</span>
        </div>
      </nav>

      <div className="max-w-lg mx-auto px-4 py-8">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6 space-y-4 text-sm text-stone-600 leading-relaxed"
        >
          <h1 className="text-lg font-semibold text-stone-800">Data & Privacy</h1>

          <section>
            <h2 className="font-medium text-stone-700 mb-1">What we collect</h2>
            <ul className="list-disc pl-5 space-y-1 text-stone-500">
              <li>Emotion data you share through cards or text</li>
              <li>Scene tags and environment context</li>
              <li>Conversation history for personalization</li>
            </ul>
          </section>

          <section>
            <h2 className="font-medium text-stone-700 mb-1">How we use it</h2>
            <p className="text-stone-500">
              Your data is used exclusively to provide personalized fragrance recommendations.
              We do not sell or share your data with third parties.
            </p>
          </section>

          <section>
            <h2 className="font-medium text-stone-700 mb-1">Data storage</h2>
            <ul className="list-disc pl-5 space-y-1 text-stone-500">
              <li>All data encrypted in transit (TLS) and at rest (AES-256)</li>
              <li>Conversation summaries retained for personalization</li>
              <li>You can delete your data at any time</li>
            </ul>
          </section>

          <section>
            <h2 className="font-medium text-stone-700 mb-1">Your rights</h2>
            <ul className="list-disc pl-5 space-y-1 text-stone-500">
              <li>View all data stored about you</li>
              <li>Request full data deletion</li>
              <li>Opt out of data collection</li>
            </ul>
          </section>

          <p className="text-xs text-stone-400 pt-2 border-t border-stone-100">
            Last updated: June 2026
          </p>
        </motion.div>
      </div>
    </div>
  );
}
