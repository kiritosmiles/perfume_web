import { motion } from "framer-motion";

interface ChipProps {
  label: string;
  emoji?: string;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export function Chip({
  label,
  emoji,
  selected = false,
  disabled = false,
  onClick,
}: ChipProps) {
  return (
    <motion.button
      whileTap={{ scale: disabled ? 1 : 0.95 }}
      onClick={onClick}
      disabled={disabled}
      className={`
        inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium
        transition-colors duration-200
        ${selected
          ? "bg-stone-800 text-stone-50 shadow-glass"
          : "glass-card text-stone-600 hover:bg-white/80"
        }
        ${disabled && !selected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
      `.trim()}
    >
      {emoji && <span className="text-base">{emoji}</span>}
      {label}
    </motion.button>
  );
}
