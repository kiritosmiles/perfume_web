import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";
import { saveLLMKey, getLLMKeyStatus, getBrowserId } from "../lib/apiClient";

const ALLERGENS_STORAGE_KEY = "perfume_allergens";

export function SettingsPage() {
  const browserId = getBrowserId();

  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com/v1");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const [alreadyConfigured, setAlreadyConfigured] = useState(false);
  const [allergens, setAllergens] = useState(
    () => localStorage.getItem(ALLERGENS_STORAGE_KEY) || ""
  );

  useEffect(() => {
    getLLMKeyStatus(browserId).then((r) => setAlreadyConfigured(r.configured));
  }, [browserId]);

  const handleSave = async () => {
    if (!apiKey.trim()) return;
    setSaving(true);
    setStatus("idle");
    try {
      await saveLLMKey({
        browser_id: browserId,
        api_key: apiKey.trim(),
        base_url: baseUrl.trim() || null,
      });
      setStatus("saved");
      setAlreadyConfigured(true);
      setApiKey("");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-dvh bg-stone-50 flex flex-col">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center">
          <a href="/" className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Home
          </a>
          <span className="ml-auto text-xs text-stone-400">Settings</span>
        </div>
      </nav>

      <div className="flex-1 flex items-start justify-center pt-16 px-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full space-y-6"
        >
          <div>
            <h1 className="text-2xl font-semibold text-stone-800">LLM API Key</h1>
            <p className="text-sm text-stone-500 mt-1">
              Use your own API key for emotion recognition and copy generation.
              Stored for 24 hours on the server.
            </p>
          </div>

          {alreadyConfigured && (
            <div className="glass-card px-4 py-3 text-sm text-green-700 bg-green-50/80 rounded-xl flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              API key configured — your key will be used for new sessions
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1.5">
                API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full rounded-xl glass-card px-4 py-3 text-sm text-stone-800
                           placeholder-stone-400 focus:outline-none focus:ring-2
                           focus:ring-stone-400 transition-shadow"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-stone-600 mb-1.5">
                Base URL (optional)
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.deepseek.com/v1"
                className="w-full rounded-xl glass-card px-4 py-3 text-sm text-stone-800
                           placeholder-stone-400 focus:outline-none focus:ring-2
                           focus:ring-stone-400 transition-shadow"
              />
            </div>
          </div>

          {status === "saved" && (
            <p className="text-sm text-green-600">✓ API key saved successfully</p>
          )}
          {status === "error" && (
            <p className="text-sm text-red-500">Failed to save. Is the server running?</p>
          )}

          <Button
            variant="primary"
            disabled={!apiKey.trim() || saving}
            onClick={handleSave}
            className="w-full"
          >
            {saving ? "Saving..." : "Save Key"}
          </Button>

          <p className="text-xs text-stone-400 text-center pt-4">
            Your key is stored encrypted in server memory and expires after 24 hours.
            You can also set <code className="bg-stone-200 px-1 rounded">LLM_API_KEY</code> in{" "}
            <code className="bg-stone-200 px-1 rounded">backend/.env</code> as the system default.
          </p>

          {/* Allergen Preferences */}
          <div className="pt-6 border-t border-stone-200 space-y-3">
            <div>
              <h2 className="text-lg font-medium text-stone-800">Allergen Preferences</h2>
              <p className="text-xs text-stone-500 mt-0.5">
                Enter ingredients you want to avoid, separated by commas.
                We'll warn you if they appear in our recommendations.
              </p>
            </div>
            <input
              type="text"
              value={allergens}
              onChange={(e) => {
                setAllergens(e.target.value);
                localStorage.setItem(ALLERGENS_STORAGE_KEY, e.target.value);
              }}
              placeholder="e.g. alcohol, linalool, citral"
              className="w-full rounded-xl glass-card px-4 py-3 text-sm text-stone-800
                         placeholder-stone-400 focus:outline-none focus:ring-2
                         focus:ring-stone-400 transition-shadow"
            />
            {allergens.trim() && (
              <p className="text-xs text-stone-400">
                Monitoring: {allergens.split(",").filter(Boolean).map((a) => a.trim()).join(", ")}
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
