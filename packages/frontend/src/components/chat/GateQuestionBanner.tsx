import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../ui/Button";

interface GateQuestionBannerProps {
  questions: string[];
  hint: string;
  onSubmit: (answer: string) => void;
  onSkip: () => void;
}

export function GateQuestionBanner({
  questions,
  hint,
  onSubmit,
  onSkip,
}: GateQuestionBannerProps) {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = useCallback(() => {
    if (!answer.trim()) return;
    setSubmitted(true);
    onSubmit(answer.trim());
  }, [answer, onSubmit]);

  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md mx-auto glass-card p-4 text-center"
      >
        <p className="text-sm text-stone-500">已收到你的回答，正在为你重新推荐...</p>
      </motion.div>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="max-w-md mx-auto"
      >
        <div className="glass-card p-5 space-y-4">
          {/* Header */}
          <div className="flex items-start gap-3">
            <span className="text-xl">🌿</span>
            <div>
              <p className="text-sm font-medium text-stone-700">
                先了解几个小细节
              </p>
              <p className="text-xs text-stone-400 mt-0.5">
                这会帮我给你更合适的推荐
              </p>
            </div>
          </div>

          {/* Questions */}
          <ul className="space-y-2">
            {questions.map((q, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-stone-600"
              >
                <span className="text-stone-300 font-medium mt-0.5">
                  {i + 1}.
                </span>
                <span>{q}</span>
              </li>
            ))}
          </ul>

          {/* Answer input */}
          <div className="space-y-2">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="在这里自由回答..."
              rows={2}
              maxLength={200}
              className="w-full resize-none rounded-lg bg-stone-100/70 px-3 py-2 text-sm
                         text-stone-700 placeholder-stone-400
                         focus:outline-none focus:ring-2 focus:ring-stone-300
                         transition-shadow"
            />
            <p className="text-xs text-stone-400 text-right">
              {answer.length}/200
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleSubmit}
              disabled={!answer.trim()}
              className="flex-1"
            >
              发送
            </Button>
            <Button
              variant="glass"
              size="sm"
              onClick={onSkip}
            >
              先推荐看看
            </Button>
          </div>

          <p className="text-xs text-stone-400 text-center">{hint}</p>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
