import { type FragranceCardUI } from "../../stores/generationStore";

interface NoteCardProps {
  cards: FragranceCardUI[];
  primaryEmotion: string;
  confidence: number;
  sceneTag?: string;
  generationId?: string;
}

function formatDate(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}.${m}.${d}`;
}

const EMOTION_EN: Record<string, string> = {
  "开心": "Joy", "难过": "Sadness", "焦虑": "Anxiety", "平静": "Calm",
  "兴奋": "Excitement", "怀旧": "Nostalgia", "浪漫": "Romance", "忧郁": "Melancholy",
};

/**
 * NoteCard — rendered offscreen for PNG export.
 * Fixed 720px width so toPng at pixelRatio:2 produces sharp 1440px image.
 */
export function NoteCard({ cards, primaryEmotion, confidence, sceneTag, generationId }: NoteCardProps) {
  const top3 = cards.slice(0, 3);

  return (
    <div style={{ width: 720 }} className="bg-[#f5f0eb] p-10 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <p className="text-xs text-stone-400 uppercase tracking-widest mb-1">Perfume Note</p>
          <h2 className="text-2xl font-semibold text-stone-800">Emotion × Fragrance</h2>
        </div>
        <p className="text-sm text-stone-500">{formatDate()}</p>
      </div>

      {/* Emotion Badge */}
      <div className="inline-flex items-center gap-3 bg-white/60 rounded-2xl px-4 py-3 mb-8">
        <div className="w-10 h-10 rounded-full bg-stone-200 flex items-center justify-center">
          <span className="text-lg">🎭</span>
        </div>
        <div>
          <p className="text-sm font-medium text-stone-700">
            {primaryEmotion} {EMOTION_EN[primaryEmotion] ? `(${EMOTION_EN[primaryEmotion]})` : ""}
          </p>
          <p className="text-xs text-stone-400">Confidence: {Math.round(confidence * 100)}%</p>
        </div>
      </div>

      {/* Fragrance Entries */}
      <div className="space-y-5">
        {top3.map((card) => (
          <div key={card.rank} className="bg-white/50 rounded-2xl p-5 flex gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-stone-800 text-white flex items-center justify-center text-sm font-bold">
              {card.rank}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2 mb-1">
                <h3 className="text-base font-semibold text-stone-800 truncate">{card.name}</h3>
                <span className="text-xs text-stone-400 flex-shrink-0">{card.brand}</span>
              </div>
              {card.notes_combination && (card.notes_combination.top?.length > 0 || card.notes_combination.middle?.length > 0 || card.notes_combination.base?.length > 0) && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {[...(card.notes_combination.top ?? []), ...(card.notes_combination.middle ?? []), ...(card.notes_combination.base ?? [])].slice(0, 6).map((note, i) => (
                    <span key={i} className="text-[10px] bg-stone-100 text-stone-600 px-2 py-0.5 rounded-full">
                      {note}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2 mb-2">
                <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                  <div className="h-full bg-stone-700 rounded-full" style={{ width: `${card.match_score}%` }} />
                </div>
                <span className="text-xs text-stone-500 font-mono">{card.match_score}%</span>
              </div>
              {card.copy_text && (
                <p className="text-xs text-stone-500 leading-relaxed line-clamp-2">
                  {card.copy_text.slice(0, 120)}{card.copy_text.length > 120 ? "..." : ""}
                </p>
              )}
            </div>
          </div>
        ))}
        {top3.length === 0 && (
          <p className="text-sm text-stone-400 text-center py-8">
            No recommendations yet — start a session to see your perfume matches
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-stone-200 flex justify-between items-end">
        <div>
          <p className="text-xs text-stone-400">Scene: {sceneTag || "Not specified"}</p>
          {generationId && (
            <p className="text-[10px] text-stone-300 mt-0.5 font-mono">ID: {generationId.slice(0, 8)}</p>
          )}
        </div>
        <p className="text-[10px] text-stone-400">perfume-ai.vercel.app</p>
      </div>
    </div>
  );
}
