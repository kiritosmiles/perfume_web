import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getMemoryTimeline, type MemoryTimelineItem } from "../lib/apiClient";
import { useAuthStore } from "../stores/authStore";

export function HistoryDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const isAuth = useAuthStore((s) => s.isAuthenticated);
  const [item, setItem] = useState<MemoryTimelineItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided");
      setLoading(false);
      return;
    }
    getMemoryTimeline(50, 0, sessionId)
      .then((res) => {
        if (res.items.length > 0) {
          setItem(res.items[0]);
        } else {
          getMemoryTimeline(100, 0).then((all) => {
            const found = all.items.find((i) => i.id === sessionId);
            if (found) {
              setItem(found);
            } else {
              setError("Conversation not found");
            }
          });
        }
        setLoading(false);
      })
      .catch((e) => {
        setError(e?.message || "Failed to load conversation");
        setLoading(false);
      });
  }, [sessionId]);

  if (loading) {
    return (
      <div className="min-h-dvh bg-stone-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="min-h-dvh bg-stone-50 flex items-center justify-center p-6">
        <div className="glass-card p-8 max-w-md text-center">
          <p className="text-2xl mb-3">🔍</p>
          <h2 className="text-lg font-semibold text-stone-700 mb-2">{error || "Not found"}</h2>
          <button onClick={() => navigate("/history")} className="text-sm text-stone-600 underline underline-offset-2">
            ← Back to history
          </button>
        </div>
      </div>
    );
  }

  const dateStr = item.created_at
    ? new Date(item.created_at).toLocaleDateString("zh-CN", {
        year: "numeric", month: "long", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      })
    : "";

  // Extract emotion profile safely
  const primaryEmotion = (item.emotion_profile as Record<string, unknown> | undefined)?.primary_emotion;
  const emotionLabel = typeof primaryEmotion === "string" ? primaryEmotion : null;

  // Extract metadata keywords safely
  const prefKeywords: string[] = [];
  if (item.metadata?.preference_keywords && Array.isArray(item.metadata.preference_keywords)) {
    for (const kw of item.metadata.preference_keywords) {
      if (typeof kw === "string") prefKeywords.push(kw);
    }
  }

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button onClick={() => navigate("/history")} className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← History
          </button>
          <span className="text-sm font-medium text-stone-700">Conversation</span>
          {isAuth ? (
            <button onClick={() => navigate("/app")} className="text-xs text-stone-400 hover:text-stone-600 transition-colors">
              App →
            </button>
          ) : <span className="w-12" />}
        </div>
      </nav>

      <div className="max-w-lg mx-auto px-4 py-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="glass-card p-5 space-y-4"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-stone-100 text-stone-500">
              {item.level}
            </span>
            {dateStr && <span className="text-xs text-stone-400">{dateStr}</span>}
          </div>

          <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-line">{item.text}</p>

          {emotionLabel && (
            <div className="bg-stone-50 rounded-lg p-3">
              <p className="text-xs text-stone-500">
                <span className="font-medium">Primary emotion: </span>
                {emotionLabel}
              </p>
            </div>
          )}

          {prefKeywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {prefKeywords.map((kw) => (
                <span key={kw} className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded-full">
                  {kw}
                </span>
              ))}
            </div>
          )}

          <div className="flex gap-2 pt-2 border-t border-stone-100">
            <button
              onClick={() => navigate("/app")}
              className="flex-1 py-2 text-xs font-medium rounded-full bg-stone-700 text-white hover:bg-stone-800 transition-colors"
            >
              Continue this topic →
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
