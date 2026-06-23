import { motion, AnimatePresence } from "framer-motion";

/** Matches CRISIS_HOTLINES in backend/app/services/safety.py */
const HOTLINES = [
  { name: "全国心理援助热线", phone: "400-161-9995", region: "全国" },
  { name: "北京心理危机研究与干预中心", phone: "010-82951332", region: "北京" },
  { name: "上海心理援助热线", phone: "021-12320-5", region: "上海" },
  { name: "生命热线 (希望24)", phone: "400-161-9995", region: "全国 24h" },
  { name: "杭州心理危机干预热线", phone: "0571-85029595", region: "浙江 24h" },
];

interface CrisisOverlayProps {
  severity: string;
  onReset: () => void;
}

export function CrisisOverlay({ severity, onReset }: CrisisOverlayProps) {
  const isBlocked = severity === "high";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-red-50/95 backdrop-blur-xl flex items-center justify-center p-6"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="max-w-md w-full space-y-6 text-center"
        >
          {/* Icon + heading */}
          <div className="space-y-3">
            <span className="text-4xl">🕊️</span>
            <h2 className="text-2xl font-semibold text-stone-800">
              我们在这里倾听你
            </h2>
            <p className="text-sm text-stone-500 leading-relaxed">
              {isBlocked
                ? "我们注意到你正在经历艰难的时刻。以下资源或许能够帮到你："
                : "我注意到一些让人担心的内容，请记得你并不孤单。"}
            </p>
          </div>

          {/* Hotline cards */}
          <div className="space-y-2 text-left">
            {HOTLINES.map((hl) => (
              <a
                key={`${hl.name}-${hl.phone}`}
                href={`tel:${hl.phone.replace(/-/g, "")}`}
                className="flex items-center gap-3 bg-white/70 backdrop-blur rounded-2xl px-4 py-3
                           hover:bg-white/90 transition-colors shadow-sm"
              >
                <span className="text-lg flex-shrink-0">📞</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-stone-700 truncate">
                    {hl.name}
                  </p>
                  <p className="text-xs text-stone-400">{hl.phone}</p>
                </div>
                <span className="text-[10px] text-stone-300 flex-shrink-0">
                  {hl.region}
                </span>
              </a>
            ))}
          </div>

          {/* Action button */}
          <button
            onClick={onReset}
            className="inline-flex items-center justify-center px-6 py-2.5 rounded-full
                       bg-stone-800 text-white text-sm font-medium
                       hover:bg-stone-700 transition-colors
                       focus:outline-none focus:ring-2 focus:ring-stone-400"
          >
            开始新会话
          </button>

          <p className="text-xs text-stone-400">
            本轮会话已暂停。开始新会话后将恢复正常推荐功能。
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
