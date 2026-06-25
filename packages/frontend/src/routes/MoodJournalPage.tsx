import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { getWeeklyJournal, type WeeklyJournalResponse } from "../lib/apiClient";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/ui/Button";

const DIMENSION_LABELS: Record<string, string> = {
  joy: "喜悦", sadness: "悲伤", anxiety: "焦虑", calm: "平静",
  excitement: "兴奋", nostalgia: "怀念", romance: "浪漫", melancholy: "忧郁",
};
const DIMENSIONS = ["joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"];
const DIM_COLORS: Record<string, string> = {
  joy: "#f59e0b", sadness: "#6b7280", anxiety: "#ef4444", calm: "#10b981",
  excitement: "#8b5cf6", nostalgia: "#f97316", romance: "#ec4899", melancholy: "#6366f1",
};

function emotionLabel(e: string | null): string {
  if (!e) return "—";
  return DIMENSION_LABELS[e] || e;
}

function WeekCard({
  week,
  label,
}: {
  week: WeeklyJournalResponse["this_week"];
  label: string;
}) {
  if (!week) return null;

  return (
    <div className="glass-card p-5 space-y-3">
      <p className="text-xs font-medium text-stone-400 uppercase tracking-wider">{label}</p>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-stone-500">Primary:</span>
        {week.primary_emotion && (
          <span
            className="px-3 py-0.5 rounded-full text-sm font-medium"
            style={{
              backgroundColor: (DIM_COLORS[week.primary_emotion] || "#f5f5f4") + "18",
              color: DIM_COLORS[week.primary_emotion] || "#78716c",
            }}
          >
            {emotionLabel(week.primary_emotion)}
          </span>
        )}
        <span className="text-xs text-stone-400">{week.session_count} active days</span>
      </div>

      {week.top_keywords.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {week.top_keywords.slice(0, 6).map((kw) => (
            <span key={kw} className="px-2 py-0.5 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-100">
              {kw}
            </span>
          ))}
        </div>
      )}

      {week.days.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {week.days.map((d) => (
            <span
              key={d.date}
              className="text-[10px] px-1.5 py-0.5 rounded"
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
    </div>
  );
}

export function MoodJournalPage() {
  const navigate = useNavigate();
  const isAuth = useAuthStore((s) => s.isAuthenticated);
  const [journal, setJournal] = useState<WeeklyJournalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weekOffset, setWeekOffset] = useState(0); // 0 = current week

  const fetchJournal = (offset: number) => {
    setLoading(true);
    setError(null);

    let weekStart: string | undefined;
    if (offset !== 0) {
      const d = new Date();
      d.setDate(d.getDate() + offset * 7);
      const monday = new Date(d);
      monday.setDate(d.getDate() - d.getDay() + 1);
      weekStart = monday.toISOString().slice(0, 10);
    }

    getWeeklyJournal(weekStart)
      .then((res) => {
        setJournal(res);
        setLoading(false);
      })
      .catch((e) => {
        setError(e?.message || "Failed to load journal");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchJournal(weekOffset);
  }, [weekOffset]);

  // Redirect non-auth users to login
  useEffect(() => {
    if (!isAuth) navigate("/login", { replace: true });
  }, [isAuth, navigate]);

  if (!isAuth) return null;

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button onClick={() => navigate("/profile")} className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Back
          </button>
          <span className="text-sm font-medium text-stone-700">Mood Journal</span>
          <div className="w-12" />
        </div>
      </nav>

      <div className="max-w-md mx-auto px-4 py-6 space-y-4">
        {/* Week navigation */}
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => setWeekOffset(weekOffset - 1)}
            className="text-sm text-stone-400 hover:text-stone-600 transition-colors"
          >
            ← Previous
          </button>
          <span className="text-xs text-stone-500 font-medium">
            {weekOffset === 0 ? "This Week" : `${Math.abs(weekOffset)} week${Math.abs(weekOffset) > 1 ? "s" : ""} ago`}
          </span>
          <button
            onClick={() => setWeekOffset(Math.min(weekOffset + 1, 0))}
            disabled={weekOffset >= 0}
            className="text-sm text-stone-400 hover:text-stone-600 disabled:text-stone-200 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>

        {loading && (
          <div className="text-center py-12">
            <div className="w-6 h-6 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin mx-auto" />
          </div>
        )}

        {error && (
          <div className="glass-card p-4 text-center text-sm text-red-500">{error}</div>
        )}

        {journal && (
          <>
            <WeekCard week={journal.this_week} label="This Week" />
            <WeekCard week={journal.last_week} label="Last Week" />

            {journal.narrative && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="glass-card p-5"
              >
                <p className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">Narrative</p>
                <p className="text-sm text-stone-600 leading-relaxed whitespace-pre-line">{journal.narrative}</p>
              </motion.div>
            )}

            <div className="text-center pt-2">
              <Button variant="glass" size="sm" onClick={() => navigate("/app")}>
                Start new conversation →
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
