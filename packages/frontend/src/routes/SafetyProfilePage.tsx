import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";
import { useAuthStore } from "../stores/authStore";
import { getBrowserId } from "../lib/apiClient";

const ALLERGENS_STORAGE_KEY = "perfume_allergens";

export function SafetyProfilePage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const browserId = getBrowserId();

  const [allergens, setAllergens] = useState(
    () => localStorage.getItem(ALLERGENS_STORAGE_KEY) || ""
  );
  const [blockedWords, setBlockedWords] = useState(
    () => localStorage.getItem("perfume_blocked_words") || ""
  );

  const saveAllergens = (val: string) => {
    setAllergens(val);
    localStorage.setItem(ALLERGENS_STORAGE_KEY, val);
  };

  const saveBlocked = (val: string) => {
    setBlockedWords(val);
    localStorage.setItem("perfume_blocked_words", val);
  };

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to={isAuthenticated ? "/app" : "/settings"} className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Back
          </Link>
          <span className="text-sm font-medium text-stone-700">Safety Profile</span>
          <div className="w-12" />
        </div>
      </nav>

      <div className="max-w-md mx-auto px-4 py-8 space-y-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="glass-card p-5 space-y-4"
        >
          <div>
            <h2 className="text-sm font-medium text-stone-700">Allergen Preferences</h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Enter ingredients you want to avoid, separated by commas.
              We will warn you if they appear in recommendations.
            </p>
          </div>
          <textarea
            value={allergens}
            onChange={(e) => saveAllergens(e.target.value)}
            placeholder="e.g. alcohol, linalool, citral..."
            rows={3}
            className="w-full resize-none rounded-xl glass-card px-4 py-3 text-sm
                       text-stone-800 placeholder-stone-400
                       focus:outline-none focus:ring-2 focus:ring-stone-400"
          />
          {allergens.trim() && (
            <div className="flex flex-wrap gap-1">
              {allergens.split(",").filter(Boolean).map((a) => (
                <span key={a.trim()} className="px-2 py-0.5 rounded-full text-xs bg-red-50 text-red-600 border border-red-100">
                  {a.trim()}
                </span>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="glass-card p-5 space-y-4"
        >
          <div>
            <h2 className="text-sm font-medium text-stone-700">Scent Profiles to Avoid</h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Notes or profiles you prefer not to see, separated by commas.
            </p>
          </div>
          <textarea
            value={blockedWords}
            onChange={(e) => saveBlocked(e.target.value)}
            placeholder="e.g. leather, tobacco, incense..."
            rows={2}
            className="w-full resize-none rounded-xl glass-card px-4 py-3 text-sm
                       text-stone-800 placeholder-stone-400
                       focus:outline-none focus:ring-2 focus:ring-stone-400"
          />
          {blockedWords.trim() && (
            <div className="flex flex-wrap gap-1">
              {blockedWords.split(",").filter(Boolean).map((w) => (
                <span key={w.trim()} className="px-2 py-0.5 rounded-full text-xs bg-stone-100 text-stone-600 border border-stone-200">
                  {w.trim()}
                </span>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="glass-card p-5 space-y-4"
        >
          <div>
            <h2 className="text-sm font-medium text-stone-700">Data & Privacy</h2>
            <p className="text-xs text-stone-500 mt-0.5">
              Browser ID: <code className="bg-stone-100 px-1 rounded">{browserId.slice(0, 8)}...</code>
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="glass" size="sm" onClick={() => {
              localStorage.removeItem(ALLERGENS_STORAGE_KEY);
              setAllergens("");
            }}>
              Clear Allergens
            </Button>
            <Button variant="glass" size="sm" onClick={() => {
              const ok = window.confirm("Clear all local preferences? This cannot be undone.");
              if (ok) {
                localStorage.removeItem(ALLERGENS_STORAGE_KEY);
                localStorage.removeItem("perfume_blocked_words");
                setAllergens("");
                setBlockedWords("");
              }
            }}>
              Reset All
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
