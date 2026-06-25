import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "../ui/Button";
import { submitHandoff } from "../../lib/apiClient";
import { useGenerationStore } from "../../stores/generationStore";

interface HumanSupportBannerProps {
  visible: boolean;
  onHandoffSubmitted?: (ticketId?: string) => void;
  onDismiss?: () => void;
}

export function HumanSupportBanner({
  visible,
  onHandoffSubmitted,
  onDismiss,
}: HumanSupportBannerProps) {
  const [expanded, setExpanded] = useState(false);
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generationId = useGenerationStore((s) => s.generationId);

  if (!visible) return null;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitHandoff({
        generation_id: generationId,
        reason: reason.trim() || undefined,
        email: email.trim() || undefined,
      });
      setSubmitted(true);
      onHandoffSubmitted?.(res.ticket_id);
    } catch (e: any) {
      setError(e?.message || "Failed to submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md mx-auto"
      >
        <div className="glass-card p-5 text-center space-y-3">
          <span className="text-3xl">🎨</span>
          <p className="text-sm font-medium text-stone-700">Request submitted!</p>
          <p className="text-xs text-stone-500 leading-relaxed">
            Our perfumer Helen Yee will review your preferences and get back to you.
            You will receive a notification when your custom fragrance is ready.
          </p>
          {onDismiss && (
            <Button variant="glass" size="sm" onClick={onDismiss}>
              Continue exploring
            </Button>
          )}
        </div>
      </motion.div>
    );
  }

  if (!expanded) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md mx-auto"
      >
        <div className="glass-card p-4 flex items-center gap-3">
          <span className="text-xl">🫱</span>
          <div className="flex-1">
            <p className="text-sm font-medium text-stone-700">Not quite right?</p>
            <p className="text-xs text-stone-500">Our perfumer can help craft something perfect for you.</p>
          </div>
          <div className="flex gap-1.5 shrink-0">
            <Button variant="primary" size="sm" onClick={() => setExpanded(true)}>
              Talk to us
            </Button>
            {onDismiss && (
              <button onClick={onDismiss} className="text-stone-400 hover:text-stone-600 text-xs px-2">
                ✕
              </button>
            )}
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-md mx-auto"
    >
      <div className="glass-card p-5 space-y-4">
        <p className="text-sm font-medium text-stone-700">Request a custom fragrance</p>
        <p className="text-xs text-stone-500">
          Tell us what you are looking for and our perfumer Helen Yee will create
          a bespoke fragrance just for you.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-stone-600 mb-1">
              What are you looking for? (optional)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. something warm and floral, less sweet than the last suggestion..."
              rows={2}
              maxLength={300}
              className="w-full resize-none rounded-lg bg-stone-100/70 px-3 py-2 text-sm
                         text-stone-700 placeholder-stone-400
                         focus:outline-none focus:ring-2 focus:ring-stone-300
                         transition-shadow"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-stone-600 mb-1">
              Email (optional — for us to reach you)
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg bg-stone-100/70 px-3 py-2 text-sm
                         text-stone-700 placeholder-stone-400
                         focus:outline-none focus:ring-2 focus:ring-stone-300"
            />
          </div>
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}

        <div className="flex gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1"
          >
            {submitting ? "Submitting..." : "Submit request"}
          </Button>
          <Button variant="glass" size="sm" onClick={() => setExpanded(false)}>
            Cancel
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
