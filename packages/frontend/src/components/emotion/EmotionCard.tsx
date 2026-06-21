import { motion } from "framer-motion";

interface EmotionCardProps {
  id: string;
  emoji: string;
  label: string;
  selected: boolean;
  disabled: boolean;
  shake?: boolean;
  onClick: () => void;
}

export function EmotionCard({
  id,
  emoji,
  label,
  selected,
  disabled,
  shake,
  onClick,
}: EmotionCardProps) {
  const isDimmed = !selected && disabled;

  return (
    <motion.button
      data-emotion-id={id}
      whileTap={isDimmed ? { scale: 1 } : { scale: 0.95 }}
      animate={
        shake
          ? { x: [0, -4, 4, -4, 4, 0] }
          : {}
      }
      transition={shake ? { duration: 0.35 } : {}}
      onClick={onClick}
      disabled={disabled && !selected}
      className={`
        flex flex-col items-center justify-center gap-2
        w-20 h-24 rounded-2xl transition-all duration-200
        font-sans text-sm
        ${isDimmed ? "opacity-40" : ""}
        ${selected
          ? "glass-card ring-2 ring-stone-800 shadow-glass-lg -translate-y-1"
          : "glass-card hover:shadow-glass-lg hover:-translate-y-0.5"
        }
      `}
    >
      <span className="text-2xl">{emoji}</span>
      <span className={`text-xs font-medium ${selected ? "text-stone-800" : "text-stone-500"}`}>
        {label}
      </span>
    </motion.button>
  );
}
