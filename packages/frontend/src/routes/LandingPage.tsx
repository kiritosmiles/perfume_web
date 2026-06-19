import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-dvh bg-stone-50 flex flex-col">
      {/* Hero section */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-center max-w-lg"
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
            className="mt-10"
          >
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate("/guest")}
            >
              Free Experience
            </Button>
          </motion.div>
        </motion.div>
      </div>

      {/* How it works */}
      <div className="pb-20 px-6">
        <div className="max-w-3xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-6">
          {[
            {
              step: "01",
              title: "Share Your Mood",
              desc: "Pick 1-2 emotion cards that match how you feel right now",
              emoji: "🎭",
            },
            {
              step: "02",
              title: "AI Understands",
              desc: "Our GraphRAG engine matches your emotions to fragrance accords",
              emoji: "🧠",
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
    </div>
  );
}
