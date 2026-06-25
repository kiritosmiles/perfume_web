import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getMemoryTimeline, type MemoryTimelineItem, type MemoryTimelineResponse } from "../lib/apiClient";
import { useAuthStore } from "../stores/authStore";

function groupByDate(items: MemoryTimelineItem[]): Map<string, MemoryTimelineItem[]> {
  const groups = new Map<string, MemoryTimelineItem[]>();
  for (const item of items) {
    const date = item.created_at ? item.created_at.slice(0, 10) : "unknown";
    if (!groups.has(date)) groups.set(date, []);
    groups.get(date)!.push(item);
  }
  return groups;
}

const LEVEL_DOT: Record<string, string> = {
  L2: "bg-violet-400",
  L3: "bg-amber-400",
};

export function HistoryListPage() {
  const navigate = useNavigate();
  const isAuth = useAuthStore((s) => s.isAuthenticated);
  const [data, setData] = useState<MemoryTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const fetchPage = (offset: number) => {
    setLoading(true);
    getMemoryTimeline(PAGE_SIZE, offset)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((e) => {
        setError(e?.message || "Failed to load history");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPage(0);
  }, []);

  const handlePrev = () => {
    const next = Math.max(0, page - 1);
    setPage(next);
    fetchPage(next * PAGE_SIZE);
  };

  const handleNext = () => {
    if (!data) return;
    const next = page + 1;
    setPage(next);
    fetchPage(next * PAGE_SIZE);
  };

  const groups = data ? groupByDate(data.items) : new Map();

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button onClick={() => navigate("/app")} className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Back
          </button>
          <span className="text-sm font-medium text-stone-700">History</span>
          {isAuth ? (
            <Link to="/app" className="text-xs text-stone-400 hover:text-stone-600 transition-colors">
              App →
            </Link>
          ) : <span className="w-12" />}
        </div>
      </nav>

      <div className="max-w-lg mx-auto px-4 py-6">
        {loading && !data && (
          <div className="text-center py-16">
            <div className="w-6 h-6 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin mx-auto" />
          </div>
        )}

        {error && (
          <div className="glass-card p-4 text-center text-sm text-red-500">{error}</div>
        )}

        {data && data.items.length === 0 && (
          <div className="text-center py-16">
            <p className="text-stone-400 text-lg">No conversations yet</p>
            <p className="text-stone-300 text-sm mt-2">Start a recommendation to see your history here.</p>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className="space-y-4">
            {Array.from(groups.entries()).map(([date, groupItems]) => (
              <motion.div key={date} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <p className="text-xs text-stone-400 font-medium mb-2">{date}</p>
                <div className="space-y-1">
                  {groupItems.map((item: MemoryTimelineItem) => {
                    // Safe extraction of emotion_profile
                    const ep = item.emotion_profile as Record<string, unknown> | undefined;
                    const itemEmotion = typeof ep?.primary_emotion === "string" ? ep.primary_emotion : null;

                    return (
                      <button
                        key={item.id}
                        onClick={() => navigate(`/history/${item.id}`)}
                        className="w-full text-left glass-card px-4 py-3 hover:bg-white/90 transition-colors"
                      >
                        <div className="flex items-start gap-3">
                          <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${LEVEL_DOT[item.level] || "bg-stone-300"}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-stone-700 line-clamp-2">{item.text}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-[10px] px-1 py-0.5 rounded font-medium text-stone-400 bg-stone-100">
                                {item.level}
                              </span>
                              {itemEmotion && (
                                <span className="text-[10px] text-stone-400">{itemEmotion}</span>
                              )}
                            </div>
                          </div>
                          <span className="text-stone-300 text-sm shrink-0">→</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            ))}

            <div className="flex justify-center gap-4 pt-4">
              <button
                onClick={handlePrev}
                disabled={page === 0}
                className="text-xs text-stone-400 hover:text-stone-600 disabled:text-stone-200 disabled:cursor-not-allowed transition-colors"
              >
                ← Previous
              </button>
              <span className="text-xs text-stone-400">Page {page + 1}</span>
              <button
                onClick={handleNext}
                disabled={!data || data.items.length < PAGE_SIZE}
                className="text-xs text-stone-400 hover:text-stone-600 disabled:text-stone-200 disabled:cursor-not-allowed transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
