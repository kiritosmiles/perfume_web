import { useState } from "react";
import { motion } from "framer-motion";
import { ScoreBar } from "./ScoreBar";
import { NotesCombination } from "./NotesCombination";
import { ActionBar } from "./ActionBar";
import { Skeleton } from "../ui/Skeleton";
import type { FragranceCardUI } from "../../stores/generationStore";
import { useGenerationStore } from "../../stores/generationStore";
import { submitFeedback } from "../../lib/apiClient";

interface FragranceCardProps {
  card: FragranceCardUI | null;
  phase: string;
  index: number;
}

/** Emotion → gradient pair for placeholder when image fails to load */
const EMOTION_GRADIENTS: Record<string, [string, string]> = {
  joy:        ["#fef9c3", "#fde68a"],
  sadness:    ["#dbeafe", "#93c5fd"],
  anxiety:    ["#e0e7ff", "#a5b4fc"],
  calm:       ["#d1fae5", "#6ee7b7"],
  excitement: ["#fce7f3", "#f9a8d4"],
  nostalgia:  ["#ede9fe", "#c4b5fd"],
  romance:    ["#ffe4e6", "#fda4af"],
  melancholy: ["#f5f0eb", "#d6d3d1"],
};

function PerfumeImage({
  imageUrl,
  name,
  primaryEmotion,
}: {
  imageUrl: string | null;
  name: string;
  primaryEmotion?: string;
}) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const grad = EMOTION_GRADIENTS[primaryEmotion || "calm"] || EMOTION_GRADIENTS.calm;

  if (!imageUrl || failed) {
    // Gradient placeholder with perfume bottle emoji
    return (
      <div
        className="relative w-full aspect-[4/5] rounded-xl overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${grad[0]}, ${grad[1]})`,
        }}
      >
        <span className="absolute inset-0 flex items-center justify-center text-5xl opacity-40 select-none">
          🧴
        </span>
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/20 to-transparent">
          <p className="text-xs text-white/90 font-medium truncate">{name}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full aspect-[4/5] rounded-xl overflow-hidden bg-stone-100">
      {!loaded && (
        <div className="absolute inset-0 bg-stone-200 animate-pulse" />
      )}
      <img
        src={imageUrl}
        alt={name}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onError={() => setFailed(true)}
        className={`w-full h-full object-cover transition-opacity duration-300 ${
          loaded ? "opacity-100" : "opacity-0"
        }`}
      />
    </div>
  );
}

export function FragranceCard({ card, phase, index }: FragranceCardProps) {
  // No card: skeleton placeholders
  if (!card) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.1 }}
        className="glass-card p-4 space-y-3 min-w-[260px] max-w-[300px]"
      >
        <div className="aspect-[4/5] rounded-xl bg-stone-200 animate-pulse" />
        <Skeleton variant="title" />
        <Skeleton variant="text" />
        <Skeleton variant="text" className="!w-1/2" />
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
        className="glass-card p-4 space-y-3 min-w-[260px] max-w-[300px] flex-shrink-0"
      >
        <PerfumeImage imageUrl={card.image_url} name={card.name} />
        <h3 className="text-sm font-semibold text-stone-800 leading-tight line-clamp-2">
          {card.name}
        </h3>
        <p className="text-xs text-stone-400">{card.brand}</p>
        <ScoreBar score={card.match_score} source={card.source} />
        <NotesCombination notes={card.notes_combination} />
        {card.allergen_warnings && card.allergen_warnings.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {card.allergen_warnings.map((w) => (
              <span
                key={w}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium
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
      className="glass-card p-4 space-y-3 min-w-[260px] max-w-[300px] flex-shrink-0"
    >
      <PerfumeImage imageUrl={card.image_url} name={card.name} />

      <div>
        <h3 className="text-sm font-semibold text-stone-800 leading-tight line-clamp-2">
          {card.name}
        </h3>
        <p className="text-xs text-stone-400 mt-0.5">{card.brand}</p>
      </div>

      <ScoreBar score={card.match_score} source={card.source} />
      <NotesCombination notes={card.notes_combination} />

      {card.allergen_warnings && card.allergen_warnings.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {card.allergen_warnings.map((w) => (
            <span
              key={w}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium
                         bg-red-100 text-red-700 border border-red-200"
            >
              ⚠ {w}
            </span>
          ))}
        </div>
      )}

      {card.fragrantica_url && (
        <a
          href={card.fragrantica_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-[10px] text-stone-400 hover:text-stone-600 underline underline-offset-2 transition-colors"
        >
          View on Fragrantica →
        </a>
      )}

      {card.copy_text && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-xs text-stone-600 leading-relaxed"
        >
          {card.copy_text.split("\n").map((line, i) => (
            <p key={i} className="mb-1">
              {line}
              {isCopyPhase && i === card.copy_text.split("\n").length - 1 && (
                <span className="inline-block w-0.5 h-3 bg-stone-400 ml-0.5 animate-pulse align-middle" />
              )}
            </p>
          ))}
        </motion.div>
      )}

      <ActionBar
        visible={isComplete}
        generationId={useGenerationStore.getState().generationId}
        cardRank={card.rank}
        onLike={() => {
          const genId = useGenerationStore.getState().generationId;
          if (genId) {
            submitFeedback({
              generation_id: genId,
              card_rank: card.rank,
              reaction: "like",
            });
          }
        }}
      />
    </motion.div>
  );
}
