import { motion } from "framer-motion";
import { ScoreBar } from "./ScoreBar";
import { NotesCombination } from "./NotesCombination";
import { ActionBar } from "./ActionBar";
import { Skeleton } from "../ui/Skeleton";
import type { FragranceCardUI } from "../../stores/generationStore";

interface FragranceCardProps {
  card: FragranceCardUI | null;
  phase: string;
  index: number;
}

export function FragranceCard({ card, phase, index }: FragranceCardProps) {
  // No card: skeleton placeholders
  if (!card) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.1 }}
        className="glass-card p-5 space-y-4"
      >
        <Skeleton variant="title" />
        <Skeleton variant="text" />
        <Skeleton variant="text" className="!w-1/2" />
        <div className="space-y-2">
          <Skeleton variant="text" className="!h-3" />
          <Skeleton variant="text" className="!h-3" />
          <Skeleton variant="text" className="!h-3" />
        </div>
      </motion.div>
    );
  }

  // Early phases: shimmer skeleton with partial info
  if (phase === "skeleton") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.15 }}
        className="glass-card p-5 space-y-4"
      >
        <h3 className="text-lg font-medium text-stone-800">{card.name}</h3>
        <p className="text-sm text-stone-500">{card.brand}</p>
        <ScoreBar score={card.match_score} source={card.source} />
        <NotesCombination notes={card.notes_combination} />
        {card.allergen_warnings && card.allergen_warnings.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {card.allergen_warnings.map((w) => (
              <span
                key={w}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
                           bg-red-100 text-red-700 border border-red-200"
              >
                ⚠ {w}
              </span>
            ))}
          </div>
        )}
      </motion.div>
    );
  }

  const isCopyPhase = phase === "copy";
  const isComplete = phase === "complete";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.15 }}
      className="glass-card p-5 space-y-4"
    >
      <div>
        <h3 className="text-lg font-medium text-stone-800">{card.name}</h3>
        <p className="text-sm text-stone-500">{card.brand}</p>
      </div>

      <ScoreBar score={card.match_score} source={card.source} />
      <NotesCombination notes={card.notes_combination} />

      {card.allergen_warnings && card.allergen_warnings.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {card.allergen_warnings.map((w) => (
            <span
              key={w}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
                         bg-red-100 text-red-700 border border-red-200"
            >
              ⚠ {w}
            </span>
          ))}
        </div>
      )}

      {card.copy_text && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-sm text-stone-600 leading-relaxed"
        >
          {card.copy_text.split("\n").map((line, i) => (
            <p key={i} className="mb-1">
              {line}
              {isCopyPhase && i === card.copy_text.split("\n").length - 1 && (
                <span className="inline-block w-0.5 h-4 bg-stone-400 ml-0.5 animate-pulse" />
              )}
            </p>
          ))}
        </motion.div>
      )}

      <ActionBar visible={isComplete} />
    </motion.div>
  );
}
