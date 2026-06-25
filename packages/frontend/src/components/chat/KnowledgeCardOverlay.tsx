/** KnowledgeCardOverlay — FR-5.5 (Phase 4).
 *
 * Auto-rotating fragrance knowledge card carousel shown during >3s loading.
 * Semi-transparent overlay with 8 pre-curated perfume ingredient facts,
 * 4s per card with fade transitions, dot progress indicator, and hint text.
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface KnowledgeCard {
  emoji: string;
  title: string;
  enName: string;
  fact: string;
}

const KNOWLEDGE_CARDS: KnowledgeCard[] = [
  {
    emoji: "🍊",
    title: "佛手柑",
    enName: "Bergamot",
    fact: "佛手柑是伯爵茶的核心香调，原产于意大利南部卡拉布里亚。其精油常用于香水的 top note，带来清新明亮的开场，也有助于缓解焦虑情绪。",
  },
  {
    emoji: "🌹",
    title: "大马士革玫瑰",
    enName: "Damask Rose",
    fact: "一公斤玫瑰精油需要约 4 吨花瓣才能提取。大马士革玫瑰只在清晨手工采摘，是香水史上最珍贵的原料之一，象征着永恒的爱与浪漫。",
  },
  {
    emoji: "🪵",
    title: "檀木",
    enName: "Sandalwood",
    fact: "印度迈索尔地区的檀木被认为是世界上最好的品种。檀木的香气温暖、奶油般柔滑，是许多经典香水的 base note，能带来平静和冥想般的感受。",
  },
  {
    emoji: "🌸",
    title: "茉莉",
    enName: "Jasmine",
    fact: "茉莉花只在夜间开放，因此必须在深夜手工采摘。它是香水的「皇后」，一公斤茉莉精油需要约 800 万朵花，比黄金还要珍贵。",
  },
  {
    emoji: "🍋",
    title: "西西里柠檬",
    enName: "Sicilian Lemon",
    fact: "意大利西西里岛的柠檬因火山土壤而独具风味。它的香气明亮、酸爽，能够瞬间提升香水的活力感。柠檬香调是夏季香水最受欢迎的 opening。",
  },
  {
    emoji: "💜",
    title: "薰衣草",
    enName: "Lavender",
    fact: "法国普罗旺斯的薰衣草田是香水爱好者的朝圣地。薰衣草是少数能同时出现在 top、middle 和 base note 中的香材，兼具清新与舒缓的特质。",
  },
  {
    emoji: "🟤",
    title: "琥珀",
    enName: "Amber",
    fact: "香水中的'琥珀'并非真正的化石，而是由安息香、劳丹脂和香草调和而成的幻想香调。它温暖、甜美、略带木质感，是秋冬香水不可或缺的基调。",
  },
  {
    emoji: "🌿",
    title: "广藿香",
    enName: "Patchouli",
    fact: "广藿香是 1960 年代嬉皮文化的象征，但它的历史可以追溯到古埃及——被用作防腐香料。如今，它是最重要的 base note 之一，赋予香水深度和持久性。",
  },
];

const CARD_INTERVAL_MS = 4000;

interface KnowledgeCardOverlayProps {
  visible: boolean;
}

export function KnowledgeCardOverlay({ visible }: KnowledgeCardOverlayProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!visible) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % KNOWLEDGE_CARDS.length);
    }, CARD_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [visible]);

  if (!visible) return null;

  const card = KNOWLEDGE_CARDS[currentIndex];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm"
    >
      <div className="max-w-sm w-full mx-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.4 }}
            className="bg-white/95 rounded-2xl p-6 shadow-xl text-center"
          >
            <div className="text-5xl mb-3">{card.emoji}</div>
            <h3 className="text-lg font-semibold text-stone-800 mb-0.5">
              {card.title}
            </h3>
            <p className="text-xs text-stone-400 mb-3 italic">{card.enName}</p>
            <p className="text-sm text-stone-600 leading-relaxed">{card.fact}</p>
          </motion.div>
        </AnimatePresence>

        {/* Progress dots */}
        <div className="flex justify-center gap-1.5 mt-4">
          {KNOWLEDGE_CARDS.map((_, i) => (
            <div
              key={i}
              className={[
                "w-1.5 h-1.5 rounded-full transition-all duration-300",
                i === currentIndex
                  ? "bg-white w-3"
                  : "bg-white/50",
              ].join(" ")}
            />
          ))}
        </div>

        <p className="text-center text-white/80 text-xs mt-4 font-medium tracking-wide">
          正在为你调配专属气味...
        </p>
      </div>
    </motion.div>
  );
}
