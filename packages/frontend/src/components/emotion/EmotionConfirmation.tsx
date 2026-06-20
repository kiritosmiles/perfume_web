import { motion, AnimatePresence } from "framer-motion";

interface EmotionConfirmationProps {
  visible: boolean;
  primaryEmotion: string;
  confidence: number;
  onCorrect?: () => void;
}

export function EmotionConfirmation({
  visible,
  primaryEmotion,
  confidence,
  onCorrect,
}: EmotionConfirmationProps) {
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
                className="h-full bg-stone-600 rounded-full transition-all duration-500"
                style={{ width: `${Math.round(confidence * 100)}%` }}
              />
            </div>
            <span className="text-xs text-stone-400">
              {Math.round(confidence * 100)}%
            </span>
          </div>
          {onCorrect && (
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
