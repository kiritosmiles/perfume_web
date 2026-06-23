import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../ui/Button";
import type { OnboardingAnswer } from "../../stores/profileStore";

const baseVector = { joy: 0, sadness: 0, anxiety: 0, calm: 0, excitement: 0, nostalgia: 0, romance: 0, melancholy: 0 };

const QUESTIONS = [
  {
    id: 1,
    text: "你平时更喜欢哪种氛围？",
    options: [
      {
        label: "🌿 自然清新",
        desc: "户外的风、绿叶、干净的棉布",
        vector: { ...baseVector, joy: 0.3, calm: 0.5, excitement: 0.1, nostalgia: 0.1 },
        tags: ["清新自然"],
      },
      {
        label: "🌹 优雅浪漫",
        desc: "烛光晚餐、花香、温柔的夜晚",
        vector: { ...baseVector, romance: 0.6, joy: 0.2, calm: 0.1, nostalgia: 0.1 },
        tags: ["优雅浪漫"],
      },
      {
        label: "🎭 个性独特",
        desc: "艺术展、小众咖啡馆、不一样的我",
        vector: { ...baseVector, excitement: 0.4, melancholy: 0.2, nostalgia: 0.2, joy: 0.1 },
        tags: ["个性独特", "小众品味"],
      },
      {
        label: "🧘 沉静内敛",
        desc: "书店、茶室、独处的时光",
        vector: { ...baseVector, calm: 0.5, melancholy: 0.2, nostalgia: 0.2, sadness: 0.1 },
        tags: ["沉静内敛"],
      },
    ],
  },
  {
    id: 2,
    text: "你对香水的态度是？",
    options: [
      { label: "日常必备，出门一定要喷", desc: "", vector: null, tags: ["实用型", "日常伴侣"] },
      { label: "特别场合才会用", desc: "", vector: null, tags: ["仪式感型", "场合驱动"] },
      { label: "喜欢收集不同的味道", desc: "", vector: null, tags: ["探索者", "香氛爱好者"] },
      { label: "刚开始了解香水", desc: "", vector: null, tags: ["新手", "好奇入门"] },
    ],
  },
  {
    id: 3,
    text: "有没有不喜欢的味道？（可选）",
    options: [
      { label: "太甜的", desc: "", vector: null, tags: ["避讳: sweet"] },
      { label: "太浓烈的", desc: "", vector: null, tags: ["避讳: spicy", "避讳: leather"] },
      { label: "太清冷的", desc: "", vector: null, tags: ["避讳: aquatic"] },
      { label: "没有特别不喜欢的", desc: "", vector: null, tags: [] },
    ],
  },
];

interface OnboardingModalProps {
  onComplete: (answers: OnboardingAnswer[]) => void;
  onSkip: () => void;
}

export function OnboardingModal({ onComplete, onSkip }: OnboardingModalProps) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<OnboardingAnswer[]>([]);
  const [exiting, setExiting] = useState(false);

  const handleSelect = useCallback(
    (option: (typeof QUESTIONS)[0]["options"][0]) => {
      const q = QUESTIONS[step];
      const answer: OnboardingAnswer = {
        question: q.id,
        option: option.label,
        mapped_vector: option.vector || null,
        mapped_tags: option.tags?.length ? option.tags : null,
      };
      const next = [...answers, answer];
      setAnswers(next);

      if (step < QUESTIONS.length - 1) {
        setStep(step + 1);
      } else {
        setExiting(true);
        setTimeout(() => onComplete(next), 300);
      }
    },
    [step, answers, onComplete],
  );

  const question = QUESTIONS[step];

  return (
    <AnimatePresence>
      {!exiting && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-sm mx-4 glass-card p-8"
          >
            {/* Progress */}
            <div className="flex gap-1 mb-6">
              {QUESTIONS.map((_, i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    i <= step ? "bg-stone-600" : "bg-stone-200"
                  }`}
                />
              ))}
            </div>

            {/* Question */}
            <h2 className="text-lg font-medium text-stone-800 mb-5">
              {question.text}
            </h2>

            {/* Options */}
            <div className="space-y-2.5">
              {question.options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => handleSelect(opt)}
                  className="w-full text-left p-3.5 rounded-xl border border-stone-200
                             hover:border-stone-400 hover:bg-stone-50
                             transition-all active:scale-[0.98]"
                >
                  <p className="text-sm font-medium text-stone-700">{opt.label}</p>
                  {opt.desc && (
                    <p className="text-xs text-stone-400 mt-0.5">{opt.desc}</p>
                  )}
                </button>
              ))}
            </div>

            {/* Skip */}
            <button
              onClick={() => {
                setExiting(true);
                setTimeout(onSkip, 300);
              }}
              className="w-full mt-4 text-xs text-stone-400 hover:text-stone-500 transition-colors"
            >
              跳过，稍后再说
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
