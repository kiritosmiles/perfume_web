import { motion } from "framer-motion";

interface ThinkingIndicatorProps {
  text?: string;
}

export function ThinkingIndicator({
  text = "Analyzing your emotions...",
}: ThinkingIndicatorProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-stone-400"
            animate={{ y: [0, -6, 0] }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              delay: i * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
      <span className="text-sm text-stone-400 italic">{text}</span>
    </div>
  );
}
