import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "../components/ui/Button";
import { useAuthStore } from "../stores/authStore";

const HOTLINES = [
  { name: "全国心理援助热线", phone: "400-161-9995", region: "全国" },
  { name: "北京心理危机研究与干预中心", phone: "010-82951332", region: "北京" },
  { name: "上海心理援助热线", phone: "021-12320-5", region: "上海" },
  { name: "生命热线 (希望24)", phone: "400-161-9995", region: "全国 24h" },
  { name: "杭州心理危机干预热线", phone: "0571-85029595", region: "浙江 24h" },
];

export function CrisisResourcesPage() {
  const navigate = useNavigate();
  const isAuth = useAuthStore((s) => s.isAuthenticated);

  return (
    <div className="min-h-dvh bg-stone-50">
      <nav className="glass-nav sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="text-stone-500 hover:text-stone-800 transition-colors text-sm">
            ← Home
          </Link>
          <span className="text-sm font-medium text-stone-700">Crisis Resources</span>
          <div className="w-12" />
        </div>
      </nav>

      <div className="max-w-md mx-auto px-4 py-8 space-y-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6 text-center space-y-3"
        >
          <span className="text-4xl">🫂</span>
          <h1 className="text-xl font-semibold text-stone-800">You are not alone</h1>
          <p className="text-sm text-stone-500 leading-relaxed">
            If you are going through a difficult time, these resources are here to help.
            You matter.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="space-y-2"
        >
          {HOTLINES.map((hl) => (
            <a
              key={`${hl.name}-${hl.phone}`}
              href={`tel:${hl.phone.replace(/-/g, "")}`}
              className="flex items-center gap-3 glass-card px-4 py-3
                         hover:bg-white/90 transition-colors"
            >
              <span className="text-lg">📞</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-stone-700 truncate">{hl.name}</p>
                <p className="text-xs text-stone-400">{hl.phone}</p>
              </div>
              <span className="text-[10px] text-stone-300 shrink-0">{hl.region}</span>
            </a>
          ))}
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="glass-card p-5 text-center space-y-3"
        >
          <h3 className="text-sm font-medium text-stone-700">Need someone to talk to right now?</h3>
          <p className="text-xs text-stone-500">
            Our AI companion is here to listen, without judgment, anytime.
          </p>
          <Button variant="primary" size="sm" onClick={() => navigate(isAuth ? "/app" : "/guest")}>
            Start a conversation
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
