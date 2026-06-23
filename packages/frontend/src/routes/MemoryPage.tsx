import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { getMemoryTimeline, type MemoryTimelineItem, type MemoryTimelineResponse } from "../lib/apiClient";
import { useAuthStore } from "../stores/authStore";

const LEVEL_COLORS = { L2: "bg-violet-100 text-violet-700", L3: "bg-amber-100 text-amber-700" } as const;

export function MemoryPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [data, setData] = useState<MemoryTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMemoryTimeline(20, 0)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-dvh bg-stone-50 flex items-center justify-center">
        <p className="text-stone-400 animate-pulse">Loading memories...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-dvh bg-stone-50 flex flex-col items-center justify-center gap-4">
        <p className="text-stone-500">Unable to load memories</p>
        <button
          onClick={() => window.location.reload()}
          className="text-sm text-stone-400 underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Home
          </Link>
          <span className="text-sm font-medium text-stone-700">AI 眼中的我</span>
          {isAuthenticated ? (
            <Link to="/app" className="text-xs text-stone-400 hover:text-stone-600 transition-colors">
              App →
            </Link>
          ) : (
            <span className="w-12" />
          )}
        </div>
      </nav>

      <div className="max-w-lg mx-auto px-4 py-8">
        {/* Stats cards */}
        {data?.stats && (
          <div className="flex gap-3 mb-8">
            <StatBadge label="L1 片段" count={data.stats.l1_count} color="bg-blue-50 text-blue-700" />
            <StatBadge label="L2 会话" count={data.stats.l2_count} color="bg-violet-50 text-violet-700" />
            <StatBadge label="L3 日级" count={data.stats.l3_count} color="bg-amber-50 text-amber-700" />
          </div>
        )}

        {/* Timeline */}
        {data?.items.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-stone-400 text-lg">还没有记忆</p>
            <p className="text-stone-300 text-sm mt-2">
              开始使用香水推荐，AI 会逐渐了解你的偏好
            </p>
          </div>
        ) : (
          <div className="space-y-1 relative before:absolute before:left-[19px] before:top-0 before:bottom-0 before:w-px before:bg-stone-200">
            {data?.items.map((item, i) => (
              <TimelineItem key={item.id} item={item} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className={`flex-1 rounded-xl px-3 py-2 text-center ${color}`}>
      <div className="text-lg font-semibold">{count}</div>
      <div className="text-xs opacity-70">{label}</div>
    </div>
  );
}

function TimelineItem({ item, index }: { item: MemoryTimelineItem; index: number }) {
  const dotColor = item.level === "L2" ? "bg-violet-400" : "bg-amber-400";
  const dateStr = item.created_at
    ? new Date(item.created_at).toLocaleDateString("zh-CN", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      })
    : "";

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="flex gap-4 pl-1 py-3"
    >
      <div className={`relative z-10 mt-1.5 w-2.5 h-2.5 rounded-full ${dotColor} ring-4 ring-stone-50 shrink-0`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${LEVEL_COLORS[item.level]}`}>
            {item.level}
          </span>
          {dateStr && <span className="text-[11px] text-stone-400">{dateStr}</span>}
        </div>
        <p className="text-sm text-stone-700 leading-relaxed">{item.text}</p>
        {Array.isArray(item.metadata?.preference_keywords) && (
          <div className="flex flex-wrap gap-1 mt-2">
            {(item.metadata.preference_keywords as string[]).map((kw) => (
              <span key={kw} className="text-[10px] px-1.5 py-0.5 bg-stone-100 text-stone-500 rounded-full">
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
