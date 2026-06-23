import { motion, AnimatePresence } from "framer-motion";

const LOW_CONFIDENCE_THRESHOLD = 0.85;

interface EmotionConfirmationProps {
  visible: boolean;
  primaryEmotion: string;
  confidence: number;
  onCorrect?: () => void;
  onConfirm?: () => void;
  onClarify?: () => void;
}

export function EmotionConfirmation({
  visible,
  primaryEmotion,
  confidence,
  onCorrect,
  onConfirm,
  onClarify,
}: EmotionConfirmationProps) {
  const isLowConfidence = confidence < LOW_CONFIDENCE_THRESHOLD;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10 }}
          className="glass-card px-6 py-4 text-center mb-4"
        >
          <p className="text-stone-500 text-sm">
            I sense you're feeling...
          </p>
          <p className="text-stone-800 text-xl font-medium mt-1">
            {primaryEmotion}
          </p>
          <div className="mt-2 flex items-center justify-center gap-2">
            <div className="h-1.5 bg-stone-200 rounded-full w-24 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${isLowConfidence ? "bg-amber-500" : "bg-stone-600"}`}
                style={{ width: `${Math.round(confidence * 100)}%` }}
              />
            </div>
            <span
              className={`text-xs ${isLowConfidence ? "text-amber-600 font-medium" : "text-stone-400"}`}
            >
              {Math.round(confidence * 100)}%
            </span>
          </div>

          {/* Low-confidence follow-up */}
          {isLowConfidence && (onConfirm || onClarify) && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-stone-500">
                Your emotion seems mixed — is this accurate?
              </p>
              <div className="flex items-center justify-center gap-2">
                {onConfirm && (
                  <button
                    onClick={onConfirm}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full
                               bg-stone-700 text-white text-xs font-medium
                               hover:bg-stone-800 transition-colors"
                  >
                    ✓ Yes, that's right
                  </button>
                )}
                {onClarify && (
                  <button
                    onClick={onClarify}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full
                               bg-stone-200/70 text-stone-600 text-xs font-medium
                               hover:bg-stone-300/70 transition-colors"
                  >
                    ↩ Let me rephrase
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Non-low-confidence correction link */}
          {!isLowConfidence && onCorrect && (
            <button
              onClick={onCorrect}
              className="mt-3 text-xs text-stone-400 hover:text-stone-600
                         underline underline-offset-2 transition-colors"
            >
              Not right? Pick again →
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
