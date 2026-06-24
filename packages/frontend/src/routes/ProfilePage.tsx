import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useProfileStore, type OnboardingAnswer } from "../stores/profileStore";
import { useAuthStore } from "../stores/authStore";
import { OnboardingModal } from "../components/onboarding/OnboardingModal";
import { EmotionTrend } from "../components/profile/EmotionTrend";
import { WeeklyJournal } from "../components/profile/WeeklyJournal";

const DIMENSION_LABELS: Record<string, string> = {
  joy: "喜悦", sadness: "悲伤", anxiety: "焦虑", calm: "平静",
  excitement: "兴奋", nostalgia: "怀旧", romance: "浪漫", melancholy: "忧郁",
};
const DIMENSIONS = ["joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"];
const DIM_COLORS = ["#f59e0b", "#6b7280", "#ef4444", "#10b981", "#8b5cf6", "#f97316", "#ec4899", "#6366f1"];

function RadarChart({ data }: { data: Record<string, number> }) {
  const size = 260;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 100;
  const levels = 5;
  const n = DIMENSIONS.length;
  const angle = (2 * Math.PI) / n;

  const point = (i: number, value: number) => {
    const r = radius * value;
    const a = angle * i - Math.PI / 2;
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  };

  const gridPath = (level: number) => {
    const r = radius * (level / levels);
    return DIMENSIONS.map((_, i) => {
      const a = angle * i - Math.PI / 2;
      const x = cx + r * Math.cos(a);
      const y = cy + r * Math.sin(a);
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ") + " Z";
  };

  const dataPath = DIMENSIONS.map((dim, i) => {
    const val = data[dim] || 0;
    const p = point(i, val);
    return `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
  }).join(" ") + " Z";

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-auto">
      {/* Grid */}
      {Array.from({ length: levels }, (_, i) => (
        <path key={i} d={gridPath(i + 1)} fill="none" stroke="#e7e5e4" strokeWidth="0.5" />
      ))}
      {/* Axis lines */}
      {DIMENSIONS.map((_, i) => {
        const p = point(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e7e5e4" strokeWidth="0.5" />;
      })}
      {/* Data fill */}
      <path d={dataPath} fill="rgba(120,113,108,0.15)" stroke="#78716c" strokeWidth="1.5" />
      {/* Data points */}
      {DIMENSIONS.map((dim, i) => {
        const p = point(i, data[dim] || 0);
        return <circle key={dim} cx={p.x} cy={p.y} r="3" fill={DIM_COLORS[i]} />;
      })}
      {/* Labels */}
      {DIMENSIONS.map((dim, i) => {
        const labelP = point(i, 1.18);
        return (
          <text key={dim} x={labelP.x} y={labelP.y} textAnchor="middle" dominantBaseline="middle" fontSize="11" fill="#78716c">
            {DIMENSION_LABELS[dim]}
          </text>
        );
      })}
    </svg>
  );
}

const VALUE_DIM_LABELS: Record<string, string> = {
  pleasure: "愉悦度", activation: "激活度", dominance: "支配度",
  social: "社交性", aesthetic: "审美性", nostalgia: "怀旧感",
};
const VALUE_DIM_ORDER = ["pleasure", "activation", "dominance", "social", "aesthetic", "nostalgia"];
const VALUE_COLORS = ["#f59e0b", "#ef4444", "#8b5cf6", "#10b981", "#ec4899", "#f97316"];

function ValueDimensionBars({ data }: { data: Record<string, number> }) {
  return (
    <div className="space-y-2">
      {VALUE_DIM_ORDER.map((key, i) => {
        const val = data[key] ?? 0;
        return (
          <div key={key} className="flex items-center gap-2">
            <span className="text-xs text-stone-500 w-12 text-right">{VALUE_DIM_LABELS[key]}</span>
            <div className="flex-1 h-3 bg-stone-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.round(Math.min(Math.max(val, 0), 1) * 100)}%`,
                  backgroundColor: VALUE_COLORS[i],
                }}
              />
            </div>
            <span className="text-xs text-stone-400 w-8">{Math.round(Math.min(Math.max(val, 0), 1) * 100)}</span>
          </div>
        );
      })}
    </div>
  );
}

function TrendLine({ data }: { data: Array<{ date: string; emotion: string; value: number }> }) {
  if (!data.length) {
    return <p className="text-sm text-stone-400 text-center py-8">对话次数还不够，多在几次推荐后就会看到趋势</p>;
  }

  const W = 320;
  const H = 120;
  const pad = { top: 10, right: 10, bottom: 20, left: 24 };
  const pw = W - pad.left - pad.right;
  const ph = H - pad.top - pad.bottom;

  const maxVal = Math.max(0.3, ...data.map((d) => d.value));
  const points = data.map((d, i) => {
    const x = pad.left + (i / Math.max(data.length - 1, 1)) * pw;
    const y = pad.top + ph - (d.value / maxVal) * ph;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      <line x1={pad.left} y1={pad.top + ph} x2={pad.left + pw} y2={pad.top + ph} stroke="#e7e5e4" strokeWidth="1" />
      {points.length > 1 && (
        <polyline points={points.join(" ")} fill="none" stroke="#78716c" strokeWidth="1.5" />
      )}
      {points.map((p, i) => {
        const [px, py] = p.split(",").map(Number);
        return <circle key={i} cx={px} cy={py} r="2.5" fill={DIM_COLORS[DIMENSIONS.indexOf(data[i].emotion) % DIM_COLORS.length] || "#78716c"} />;
      })}
    </svg>
  );
}

export function ProfilePage() {
  const navigate = useNavigate();
  const { profile, conversationCount, loading, error, valueDimensions, fetchProfile, submitOnboarding } = useProfileStore();
  const isAuth = useAuthStore((s) => !!s.user);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (!isAuth) {
      navigate("/login");
      return;
    }
    fetchProfile();
  }, [isAuth, navigate, fetchProfile]);

  useEffect(() => {
    if (profile && !profile.questionnaire_completed && conversationCount === 0) {
      setShowOnboarding(true);
    }
  }, [profile, conversationCount]);

  const handleOnboardingComplete = useCallback(
    async (answers: OnboardingAnswer[]) => {
      await submitOnboarding(answers);
      setShowOnboarding(false);
    },
    [submitOnboarding],
  );

  const handleOnboardingSkip = useCallback(() => {
    setShowOnboarding(false);
  }, []);

  if (!isAuth) return null;

  return (
    <div className="min-h-dvh bg-stone-50">
      {showOnboarding && (
        <OnboardingModal onComplete={handleOnboardingComplete} onSkip={handleOnboardingSkip} />
      )}

      {/* Header */}
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <button
            onClick={() => navigate("/app")}
            className="text-stone-500 hover:text-stone-800 transition-colors text-sm"
          >
            ← Back
          </button>
          <span className="text-sm font-medium text-stone-700">AI 眼中的你</span>
          <div className="w-12" />
        </div>
      </nav>

      <div className="max-w-md mx-auto px-4 py-6 space-y-5">
        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin w-6 h-6 border-2 border-stone-300 border-t-stone-600 rounded-full mx-auto" />
          </div>
        )}

        {error && (
          <div className="glass-card p-4 text-center text-sm text-red-500">{error}</div>
        )}

        {!loading && !error && profile && (
          <>
            {/* Personality tags */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-card p-5"
            >
              <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                人格标签
              </h3>
              <div className="flex flex-wrap gap-2">
                {profile.personality_tags.length > 0 ? (
                  profile.personality_tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-3 py-1 rounded-full text-sm bg-stone-100 text-stone-600"
                    >
                      {tag}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-stone-400">用几次之后，AI 会更了解你的风格</p>
                )}
              </div>
            </motion.div>

            {/* Emotion radar */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card p-5"
            >
              <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-2">
                情绪画像
              </h3>
              {Object.keys(profile.emotion_tendency).length > 0 ? (
                <RadarChart data={profile.emotion_tendency} />
              ) : (
                <p className="text-sm text-stone-400 text-center py-8">完成首次对话后会显示情绪画像</p>
              )}
            </motion.div>

            {/* Value dimensions bar chart (FR-2.5) */}
            {valueDimensions && Object.keys(valueDimensions).length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
                className="glass-card p-5"
              >
                <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                  价值维度
                </h3>
                <ValueDimensionBars data={valueDimensions} />
              </motion.div>
            )}

            {/* Preferred accords */}
            {profile.preferred_accords.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card p-5"
              >
                <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                  偏好香调
                </h3>
                <div className="flex flex-wrap gap-2">
                  {profile.preferred_accords.map((acc) => (
                    <span
                      key={acc}
                      className="px-3 py-1 rounded-full text-sm bg-amber-50 text-amber-700 border border-amber-100"
                    >
                      {acc}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Gift history */}
            {profile.gift_history.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="glass-card p-5"
              >
                <h3 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                  送礼历史
                </h3>
                <div className="space-y-2">
                  {profile.gift_history.map((g, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm">
                      <span className="text-stone-400">{g.recipient}</span>
                      <span className="text-stone-300">·</span>
                      <span className="text-stone-500">{g.occasion}</span>
                      <span className="text-stone-300">·</span>
                      <span className="text-stone-600 font-medium">{g.perfume}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Emotion Trend (F4) */}
            <EmotionTrend />

            {/* Weekly Journal (F4) */}
            <WeeklyJournal />

            {/* Profile metadata */}
            <div className="text-center space-y-1 pb-8">
              <p className="text-xs text-stone-400">
                画像级别: {profile.profile_level === "full" ? "完整画像" : "基础画像"}
                {" · "}已对话 {conversationCount} 次
              </p>
              <p className="text-xs text-stone-300">
                这些信息仅对你可见
              </p>
            </div>
          </>
        )}

        {!loading && !error && !profile && (
          <div className="text-center py-16">
            <p className="text-stone-400 text-sm">尚未创建画像</p>
            <p className="text-stone-300 text-xs mt-1">完成第一次推荐后会开始构建你的画像</p>
          </div>
        )}
      </div>
    </div>
  );
}
