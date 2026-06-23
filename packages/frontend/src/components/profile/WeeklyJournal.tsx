import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { getWeeklyJournal, type WeeklyJournalResponse } from "../../lib/apiClient";

const DIMENSION_LABELS: Record<string, string> = {
  joy: "喜悦", sadness: "悲伤", anxiety: "焦虑", calm: "平静",
  excitement: "兴奋", nostalgia: "怀旧", romance: "浪漫", melancholy: "忧郁",
};
const DIMENSIONS = ["joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"];
const DIM_COLORS: Record<string, string> = {
  joy: "#f59e0b", sadness: "#6b7280", anxiety: "#ef4444", calm: "#10b981",
  excitement: "#8b5cf6", nostalgia: "#f97316", romance: "#ec4899", melancholy: "#6366f1",
};

function emotionLabel(emotion: string | null): string {
  if (!emotion) return "—";
  return DIMENSION_LABELS[emotion] || emotion;
}

function WeekComparisonRadar({
  thisWeek,
  lastWeek,
}: {
  thisWeek: Record<string, number>;
  lastWeek: Record<string, number> | null;
}) {
  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 85;
  const levels = 4;
  const n = DIMENSIONS.length;
  const angle = (2 * Math.PI) / n;

  const point = (i: number, value: number) => {
    const r = radius * Math.min(value, 1);
    const a = angle * i - Math.PI / 2;
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  };

  const dataPath = (data: Record<string, number>) =>
    DIMENSIONS.map((dim, i) => {
      const val = data[dim] || 0;
      const p = point(i, val);
      return `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
    }).join(" ") + " Z";

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-auto max-w-[220px] mx-auto">
      {/* Grid */}
      {Array.from({ length: levels }, (_, i) => {
        const r = radius * ((i + 1) / levels);
        const path = DIMENSIONS.map((_, j) => {
          const a = angle * j - Math.PI / 2;
          const x = cx + r * Math.cos(a);
          const y = cy + r * Math.sin(a);
          return `${j === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
        }).join(" ") + " Z";
        return <path key={i} d={path} fill="none" stroke="#e7e5e4" strokeWidth="0.5" />;
      })}
      {/* Axis */}
      {DIMENSIONS.map((_, i) => {
        const p = point(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e7e5e4" strokeWidth="0.5" />;
      })}
      {/* Last week (gray fill) */}
      {lastWeek && (
        <path d={dataPath(lastWeek)} fill="rgba(168,162,158,0.12)" stroke="#a8a29e" strokeWidth="1" strokeDasharray="3,2" />
      )}
      {/* This week */}
      <path d={dataPath(thisWeek)} fill="rgba(120,113,108,0.15)" stroke="#78716c" strokeWidth="1.5" />
      {/* Labels */}
      {DIMENSIONS.map((dim, i) => {
        const labelP = point(i, 1.2);
        return (
          <text key={dim} x={labelP.x} y={labelP.y} textAnchor="middle" dominantBaseline="middle" fontSize="9" fill="#a8a29e">
            {DIMENSION_LABELS[dim]}
          </text>
        );
      })}
    </svg>
  );
}

export function WeeklyJournal() {
  const [journal, setJournal] = useState<WeeklyJournalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJournal = useCallback((weekStart?: string) => {
    setLoading(true);
    setError(null);
    getWeeklyJournal(weekStart)
      .then((res) => {
        setJournal(res);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "加载失败");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchJournal();
  }, [fetchJournal]);

  // Navigate to previous week
  const goToPrevWeek = () => {
    if (!journal) return;
    const current = new Date(journal.week_start + "T00:00:00");
    current.setDate(current.getDate() - 7);
    const prev = current.toISOString().slice(0, 10);
    fetchJournal(prev);
  };

  // Navigate to next week (only if not at current)
  const goToNextWeek = () => {
    if (!journal) return;
    const current = new Date(journal.week_start + "T00:00:00");
    current.setDate(current.getDate() + 7);
    const next = current.toISOString().slice(0, 10);
    // Don't go beyond current week
    const today = new Date();
    const thisMonday = new Date(today);
    thisMonday.setDate(today.getDate() - today.getDay() + 1);
    if (current > thisMonday) return;
    fetchJournal(next);
  };

  if (loading) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">情绪周记</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-24 bg-stone-100 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">情绪周记</h3>
        <p className="text-sm text-stone-400 text-center py-6">{error}</p>
      </div>
    );
  }

  if (!journal || !journal.this_week) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">情绪周记</h3>
        <p className="text-sm text-stone-400 text-center py-6">
          该周暂无情绪记录
        </p>
      </div>
    );
  }

  const thisWeek = journal.this_week;
  const lastWeek = journal.last_week;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="glass-card p-5 space-y-4"
    >
      {/* Header with navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={goToPrevWeek}
          className="text-stone-400 hover:text-stone-600 transition-colors text-sm px-1"
          aria-label="上一周"
        >
          ←
        </button>
        <div className="text-center">
          <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider">情绪周记</h3>
          <p className="text-sm text-stone-600 mt-0.5">
            {journal.week_start} ~ {journal.week_end}
          </p>
        </div>
        <button
          onClick={goToNextWeek}
          className="text-stone-400 hover:text-stone-600 transition-colors text-sm px-1"
          aria-label="下一周"
        >
          →
        </button>
      </div>

      {/* Primary emotion + keywords summary */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm text-stone-500">本周主情绪</span>
        <span
          className="px-3 py-1 rounded-full text-sm font-medium"
          style={{
            backgroundColor: (thisWeek.primary_emotion && DIM_COLORS[thisWeek.primary_emotion] + "18") || "#f5f5f4",
            color: (thisWeek.primary_emotion && DIM_COLORS[thisWeek.primary_emotion]) || "#78716c",
          }}
        >
          {emotionLabel(thisWeek.primary_emotion)}
        </span>
        <span className="text-sm text-stone-400">
          · {thisWeek.session_count} 天活跃
        </span>
      </div>

      {/* Top keywords */}
      {thisWeek.top_keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {thisWeek.top_keywords.slice(0, 6).map((kw) => (
            <span key={kw} className="px-2 py-0.5 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-100">
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Radar comparison: this week vs last week */}
      {lastWeek && (
        <div>
          <p className="text-xs text-stone-400 mb-2 flex items-center gap-3 justify-center">
            <span className="inline-flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-stone-400 inline-block" /> 本周
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-stone-300 inline-block" style={{ borderTop: "1px dashed #a8a29e" }} /> 上周
            </span>
          </p>
          <WeekComparisonRadar thisWeek={thisWeek.emotion_vector} lastWeek={lastWeek.emotion_vector} />
        </div>
      )}

      {!lastWeek && (
        <WeekComparisonRadar thisWeek={thisWeek.emotion_vector} lastWeek={null} />
      )}

      {/* Narrative */}
      <div className="bg-stone-50 rounded-lg p-4">
        <p className="text-sm text-stone-600 leading-relaxed whitespace-pre-line">
          {journal.narrative}
        </p>
      </div>

      {/* Daily breakdown */}
      {thisWeek.days.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs text-stone-400">每日情绪：</span>
          {thisWeek.days.map((d) => (
            <span
              key={d.date}
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: (d.primary_emotion && DIM_COLORS[d.primary_emotion] + "14") || "#f5f5f4",
              }}
              title={`${d.date.slice(5)}: ${emotionLabel(d.primary_emotion)}`}
            >
              {d.date.slice(5)}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}
