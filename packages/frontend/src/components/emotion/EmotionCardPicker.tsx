import { useState, useCallback } from "react";
import { EmotionCard } from "./EmotionCard";

const EMOTION_CARDS = [
  { id: "joy", emoji: "😊", label: "开心" },
  { id: "sadness", emoji: "😢", label: "难过" },
  { id: "anxiety", emoji: "😰", label: "焦虑" },
  { id: "calm", emoji: "😌", label: "平静" },
  { id: "excitement", emoji: "🎉", label: "兴奋" },
  { id: "nostalgia", emoji: "🥺", label: "怀旧" },
  { id: "romance", emoji: "💕", label: "浪漫" },
  { id: "melancholy", emoji: "🌧️", label: "忧郁" },
];

interface EmotionCardPickerProps {
  selectedIds: string[];
  onToggle: (id: string) => void;
  maxSelection?: number;
}

export function EmotionCardPicker({
  selectedIds,
  onToggle,
  maxSelection = 2,
}: EmotionCardPickerProps) {
  const [shakeKey, setShakeKey] = useState(0);

  const handleToggle = useCallback(
    (id: string) => {
      const atMax = selectedIds.length >= maxSelection;
      const isSelected = selectedIds.includes(id);
      if (atMax && !isSelected) {
        // Over-limit: trigger shake animation on cards
        setShakeKey((k) => k + 1);
        return;
      }
      onToggle(id);
    },
    [selectedIds, maxSelection, onToggle],
  );

  const atMax = selectedIds.length >= maxSelection;

  return (
    <div>
      <p className="text-center text-sm text-stone-500 mb-4">
        选择 1-2 张最能代表你此刻心情的卡片
      </p>
      <div className="grid grid-cols-4 gap-3 justify-items-center">
        {EMOTION_CARDS.map((card) => {
          const isSelected = selectedIds.includes(card.id);
          const isDisabled = atMax && !isSelected;
          return (
            <EmotionCard
              key={card.id}
              id={card.id}
              emoji={card.emoji}
              label={card.label}
              selected={isSelected}
              disabled={isDisabled}
              shake={shakeKey > 0 && isDisabled}
              onClick={() => handleToggle(card.id)}
            />
          );
        })}
      </div>
    </div>
  );
}
