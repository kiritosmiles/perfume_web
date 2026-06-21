interface SharePayloadData {
  recommendations: Array<{
    rank: number;
    name: string;
    brand: string;
    notes_combination?: string[];
    match_score: number;
    copy_text?: string;
  }>;
  emotion: {
    primary_emotion: string;
    confidence: number;
  };
  scene_tag?: string | null;
}

export function ShareCard({ payload }: { payload: SharePayloadData }) {
  const { emotion, recommendations } = payload;
  const top3 = recommendations.slice(0, 3);

  return (
    <div className="min-h-dvh bg-gradient-to-br from-[#f5f0eb] via-[#e8e0d5] to-[#d5c8b5] flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
        <div className="text-center mb-8">
          <p className="text-xs text-stone-400 uppercase tracking-widest mb-2">Perfume AI</p>
          <div className="inline-flex items-center gap-2 bg-white/60 rounded-full px-4 py-2 mb-3">
            <span className="text-sm text-stone-600">{emotion.primary_emotion}</span>
            <span className="text-xs text-stone-400">{Math.round(emotion.confidence * 100)}% match</span>
          </div>
        </div>
        <div className="space-y-4">
          {top3.map((card) => (
            <div key={card.rank} className="bg-white/70 backdrop-blur rounded-2xl p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-stone-800 text-white flex items-center justify-center text-xs font-bold">
                  {card.rank}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-stone-800 truncate">{card.name}</h3>
                  <p className="text-xs text-stone-400 mb-2">{card.brand}</p>
                  {card.notes_combination && card.notes_combination.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {card.notes_combination.slice(0, 4).map((note, i) => (
                        <span key={i} className="text-[10px] bg-stone-100 text-stone-500 px-2 py-0.5 rounded-full">{note}</span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <div className="flex-1 h-1 bg-stone-200 rounded-full overflow-hidden">
                      <div className="h-full bg-stone-700 rounded-full" style={{ width: `${card.match_score}%` }} />
                    </div>
                    <span className="text-xs text-stone-500">{card.match_score}%</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="text-center mt-8">
          <a href="/" className="inline-block text-sm text-stone-600 hover:text-stone-800 bg-white/60 backdrop-blur rounded-full px-6 py-3 transition-all hover:shadow-md">
            Experience your own →
          </a>
          <p className="text-xs text-stone-400 mt-4">perfume-ai.vercel.app</p>
        </div>
      </div>
    </div>
  );
}
