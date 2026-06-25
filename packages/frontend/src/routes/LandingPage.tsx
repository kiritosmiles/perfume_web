import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";
import { EmotionCard } from "../components/emotion/EmotionCard";
import { SceneTagChips } from "../components/chat/SceneTagChips";
import { useAuthStore } from "../stores/authStore";

const EMOTION_CARD_3D = [
  { emoji: "😉", label: "开心", color: "#fef3c7" },
  { emoji: "😩", label: "难过", color: "#dbeafe" },
  { emoji: "😹", label: "焦虑", color: "#fce7f3" },
  { emoji: "😘", label: "平静", color: "#d1fae5" },
  { emoji: "😀", label: "兴奋", color: "#fef9c3" },
  { emoji: "😶", label: "怀念", color: "#ede9fe" },
  { emoji: "😄", label: "浪漫", color: "#ffe4e6" },
  { emoji: "😪💔", label: "忧郁", color: "#e0e7ff" },
] as const;

// Quick emotion cards for the GuestEntrySection
const QUICK_CARDS = [
  { id: "joy", emoji: "😉", label: "开心" },
  { id: "calm", emoji: "😘", label: "平静" },
  { id: "excitement", emoji: "😀", label: "兴奋" },
  { id: "romance", emoji: "😄", label: "浪漫" },
];

export function LandingPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const logout = useAuthStore((s) => s.logout);

  // P1.2: Check for guest session in localStorage
  const hasGuestSession = !!localStorage.getItem("perfume_browser_id") && !isAuthenticated;

  // P1.3: Guest entry quick select
  const [guestCardIds, setGuestCardIds] = useState<string[]>([]);
  const [guestSceneTag, setGuestSceneTag] = useState<string>("");

  const handleGuestToggleCard = useCallback((id: string) => {
    setGuestCardIds((prev) => {
      if (prev.includes(id)) return prev.filter((c) => c !== id);
      if (prev.length >= 2) return prev;
      return [...prev, id];
    });
  }, []);

  const handleGuestToggleScene = useCallback((id: string) => {
    setGuestSceneTag((prev) => (prev === id ? "" : id));
  }, []);

  const handleGuestStart = () => {
    const params = new URLSearchParams();
    if (guestCardIds.length > 0) params.set("card_ids", guestCardIds.join(","));
    if (guestSceneTag) params.set("scene", guestSceneTag);
    const qs = params.toString();
    navigate(`/guest${qs ? `?${qs}` : ""}`);
  };

  // P1.2: Determine CTA based on user state
  const ctaConfig = (() => {
    if (isAuthenticated) {
      return {
        primary: { label: "Continue Your Journey →", path: "/app" },
        secondary: [
          { label: "Memories", path: "/memory" },
          { label: "Profile", path: "/profile" },
          { label: "Settings", path: "/settings" },
        ],
        extra: (
          <button
            onClick={() => { logout(); navigate("/"); }}
            className="text-xs text-stone-400 hover:text-stone-600 transition-colors underline underline-offset-2"
          >
            Logout
          </button>
        ),
      };
    }
    if (hasGuestSession) {
      return {
        primary: { label: "Continue Your Exploration →", path: "/guest" },
        secondary: [
          { label: "Sign In", path: "/login" },
          { label: "Register", path: "/register" },
        ],
        extra: null,
      };
    }
    return {
      primary: { label: "✨ Free Experience", path: "/guest" },
      secondary: [
        { label: "Sign In", path: "/login" },
        { label: "Register", path: "/register" },
      ],
      extra: null,
    };
  })();

  return (
    <div className="min-h-dvh bg-stone-50 flex flex-col overflow-hidden">
      {/* Hero section */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20 relative">
        {/* 3D rotating card ring */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-40">
          <motion.div
            className="relative w-[320px] h-[320px] sm:w-[400px] sm:h-[400px]"
            animate={{ rotate: 360 }}
            transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
            style={{ perspective: 600 }}
          >
            {EMOTION_CARD_3D.map((card, i) => {
              const angle = (i / EMOTION_CARD_3D.length) * Math.PI * 2;
              const radius = 140;
              const x = Math.cos(angle) * radius;
              const y = Math.sin(angle) * radius;
              return (
                <motion.div
                  key={card.label}
                  className="absolute left-1/2 top-1/2 glass-card rounded-xl
                             w-16 h-20 flex flex-col items-center justify-center gap-1
                             shadow-glass"
                  style={{
                    x: x - 32,
                    y: y - 40,
                    rotateY: (i / EMOTION_CARD_3D.length) * 360,
                  }}
                  animate={{
                    rotateY: [(i / EMOTION_CARD_3D.length) * 360,
                              (i / EMOTION_CARD_3D.length) * 360 + 360],
                  }}
                  transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                >
                  <span className="text-xl">{card.emoji}</span>
                  <span className="text-[10px] font-medium text-stone-500">
                    {card.label}
                  </span>
                </motion.div>
              );
            })}
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-center max-w-lg relative z-10"
        >
          <h1 className="text-5xl sm:text-6xl font-light text-stone-800 tracking-tight leading-tight">
            Discover your scent
            <br />
            through emotions
          </h1>
          <p className="mt-6 text-lg text-stone-500 font-light leading-relaxed">
            情绪人格 × 香水 AI Agent
            <br />
            让香气与你的情绪共鸣
          </p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="mt-10 flex flex-col items-center gap-4"
          >
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate(ctaConfig.primary.path)}
            >
              {ctaConfig.primary.label}
            </Button>
            <div className="flex items-center gap-3 text-sm text-stone-400">
              {ctaConfig.secondary.map((item, i) => (
                <span key={item.path} className="flex items-center gap-3">
                  <button
                    onClick={() => navigate(item.path)}
                    className="hover:text-stone-600 transition-colors underline underline-offset-2"
                  >
                    {item.label}
                  </button>
                  {i < ctaConfig.secondary.length - 1 && <span>·</span>}
                </span>
              ))}
              {ctaConfig.extra && (
                <>
                  <span>·</span>
                  {ctaConfig.extra}
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* How it works */}
      <div className="pb-12 px-6">
        <div className="max-w-3xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            {
              step: "01",
              title: "Share Your Mood",
              desc: "Pick 1-2 emotion cards that match how you feel right now",
              emoji: "🕁",
            },
            {
              step: "02",
              title: "AI Understands",
              desc: "Our GraphRAG engine matches your emotions to fragrance accords",
              emoji: "🕥",
            },
            {
              step: "03",
              title: "Discover Scents",
              desc: "Get personalized perfume recommendations in real-time",
              emoji: "✨",
            },
          ].map((item, i) => (
            <motion.div
              key={item.step}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.15 }}
              className="glass-card p-6 text-center"
            >
              <span className="text-3xl">{item.emoji}</span>
              <p className="text-xs text-stone-400 mt-3 font-mono">{item.step}</p>
              <h3 className="text-base font-medium text-stone-800 mt-1">
                {item.title}
              </h3>
              <p className="text-sm text-stone-500 mt-2 leading-relaxed">
                {item.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* P1.3: GuestEntrySection — Quick emotion + scene picker for new visitors */}
      {!isAuthenticated && (
        <div className="pb-20 px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="max-w-lg mx-auto glass-card p-6 text-center space-y-5"
          >
            <p className="text-sm font-medium text-stone-600">
              No account needed — start right now 🎶
            </p>

            {/* Quick emotion cards (single/multi select, max 2) */}
            <div className="flex justify-center gap-2">
              {QUICK_CARDS.map((card) => {
                const isSelected = guestCardIds.includes(card.id);
                return (
                  <EmotionCard
                    key={card.id}
                    id={card.id}
                    emoji={card.emoji}
                    label={card.label}
                    selected={isSelected}
                    disabled={guestCardIds.length >= 2 && !isSelected}
                    shake={false}
                    onClick={() => handleGuestToggleCard(card.id)}
                  />
                );
              })}
            </div>

            {/* Scene tags */}
            <div className="flex justify-center">
              <SceneTagChips
                selected={guestSceneTag ? [guestSceneTag] : []}
                onToggle={(id) => handleGuestToggleScene(id)}
              />
            </div>

            <Button
              variant="primary"
              disabled={guestCardIds.length === 0}
              onClick={handleGuestStart}
              className="w-full sm:w-auto"
            >
              Start Exploring
            </Button>

            <p className="text-xs text-stone-400">
              Pick your mood and discover your scent instantly.
            </p>
          </motion.div>
        </div>
      )}
    </div>
  );
}
