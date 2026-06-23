import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getEmotionTrend, type EmotionTrendPoint } from "../../lib/apiClient";

const DIMENSION_LABELS: Record<string, string> = {
  joy: "喜悦", sadness: "悲伤", anxiety: "焦虑", calm: "平静",
  excitement: "兴奋", nostalgia: "怀旧", romance: "浪漫", melancholy: "忧郁",
};
const DIMENSIONS = ["joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"];
const DIM_COLORS: Record<string, string> = {
  joy: "#f59e0b", sadness: "#6b7280", anxiety: "#ef4444", calm: "#10b981",
  excitement: "#8b5cf6", nostalgia: "#f97316", romance: "#ec4899", melancholy: "#6366f1",
};

function emotionColor(emotion: string | null): string {
  if (!emotion) return "#d6d3d1";
  return DIM_COLORS[emotion] || "#78716c";
}

function emotionLabel(emotion: string | null): string {
  if (!emotion) return "—";
  return DIMENSION_LABELS[emotion] || emotion;
}

export function EmotionTrend() {
  const [data, setData] = useState<EmotionTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getEmotionTrend(30)
      .then((res) => {
        if (!cancelled) {
          setData(res.data);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "加载失败");
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">情绪趋势</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-32 bg-stone-100 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">情绪趋势</h3>
        <p className="text-sm text-stone-400 text-center py-8">{error}</p>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="glass-card p-5">
        <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">情绪趋势</h3>
        <p className="text-sm text-stone-400 text-center py-8">
          情绪数据收集中 — 用几次推荐后，这里会展示你的情绪变化趋势
        </p>
      </div>
    );
  }

  // Build the SVG line chart
  const W = 640;
  const H = 200;
  const pad = { top: 20, right: 16, bottom: 30, left: 32 };
  const pw = W - pad.left - pad.right;
  const ph = H - pad.top - pad.bottom;

  // Map each day to a primary emotion score (we use the dominant value for the bar)
  const points = data.map((d, i) => {
    const x = pad.left + (i / Math.max(data.length - 1, 1)) * pw;
    const primaryVal = d.primary_emotion && d.emotion_scores[d.primary_emotion]
      ? d.emotion_scores[d.primary_emotion]
      : 0.15;
    const y = pad.top + ph - primaryVal * ph;
    return { x, y, emotion: d.primary_emotion, date: d.date, value: primaryVal };
  });

  // Polyline path
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  // Date labels (show ~6 evenly spaced)
  const labelIndices: number[] = [];
  if (data.length <= 7) {
    data.forEach((_, i) => labelIndices.push(i));
  } else {
    const step = Math.floor(data.length / 6);
    for (let i = 0; i < data.length; i += step) {
      labelIndices.push(i);
    }
    if (labelIndices[labelIndices.length - 1] !== data.length - 1) {
      labelIndices.push(data.length - 1);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="glass-card p-5"
    >
      <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
        情绪趋势 · 近{data.length}天
      </h3>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        {/* Horizontal grid lines */}
        {[0.25, 0.5, 0.75, 1.0].map((level) => {
          const y = pad.top + ph - level * ph;
          return (
            <g key={level}>
              <line x1={pad.left} y1={y} x2={pad.left + pw} y2={y} stroke="#e7e5e4" strokeWidth="0.5" />
              <text x={pad.left - 4} y={y} textAnchor="end" dominantBaseline="middle" fontSize="9" fill="#a8a29e">
                {Math.round(level * 100)}%
              </text>
            </g>
          );
        })}

        {/* Trend line */}
        {points.length > 1 && (
          <polyline points={points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")}
            fill="none" stroke="#78716c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          />
        )}

        {/* Data dots */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3.5"
            fill={emotionColor(p.emotion)} stroke="#fff" strokeWidth="1"
          />
        ))}

        {/* Date labels */}
        {labelIndices.map((i) => {
          const p = points[i];
          const shortDate = p.date.slice(5); // MM-DD
          return (
            <text key={i} x={p.x} y={H - 4} textAnchor="middle" fontSize="9" fill="#a8a29e">
              {shortDate}
            </text>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mt-3 justify-center">
        {DIMENSIONS.filter(d => data.some(p => p.primary_emotion === d)).slice(0, 5).map((dim) => (
          <span key={dim} className="inline-flex items-center gap-1 text-xs text-stone-500">
            <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: DIM_COLORS[dim] }} />
            {DIMENSION_LABELS[dim]}
          </span>
        ))}
      </div>
    </motion.div>
  );
}
