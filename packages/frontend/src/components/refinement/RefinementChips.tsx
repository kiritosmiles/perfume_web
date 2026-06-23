import { motion } from "framer-motion";

const REFINEMENT_OPTIONS = [
  { key: "sweeter", label: "更甜", emoji: "🍬" },
  { key: "fresher", label: "更清新", emoji: "🍃" },
  { key: "more_floral", label: "花香调", emoji: "🌸" },
  { key: "more_woody", label: "木质调", emoji: "🪵" },
  { key: "warmer", label: "更温暖", emoji: "☀️" },
  { key: "cooler", label: "更清冷", emoji: "❄️" },
  { key: "lighter", label: "更轻盈", emoji: "💨" },
  { key: "stronger", label: "更浓郁", emoji: "💪" },
];

interface RefinementChipsProps {
  onSelect: (key: string) => void;
  disabled?: boolean;
}

export function RefinementChips({ onSelect, disabled }: RefinementChipsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-2"
    >
      <p className="text-xs text-stone-400 text-center">Not quite? Refine:</p>
      <div className="flex flex-wrap justify-center gap-1.5">
        {REFINEMENT_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => onSelect(opt.key)}
            disabled={disabled}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-full
                       text-xs font-medium transition-all
                       bg-white/60 border border-stone-200/50
                       text-stone-600 hover:bg-stone-100 hover:text-stone-800
                       hover:border-stone-300 hover:shadow-sm
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="text-sm">{opt.emoji}</span>
            {opt.label}
          </button>
        ))}
      </div>
    </motion.div>
  );
}
