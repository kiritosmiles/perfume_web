/** Session mode selector — FR-1.5 (Phase 4).
 *
 * Three modes that control how the AI loads context and generates recommendations:
 * - Context ("今天的我"): Current mood + session context only (default)
 * - Identity ("一直的我"): Stable personality profile + full history
 * - Novelty ("想尝试的我"): Maximize diversity, suppress historical preferences
 *
 * Persisted in sessionStore.sessionMode.
 */

export type SessionMode = "context" | "identity" | "novelty";

interface SessionModeOption {
  id: SessionMode;
  emoji: string;
  label: string;
  hint: string;
}

const MODES: SessionModeOption[] = [
  {
    id: "context",
    emoji: "🌊",
    label: "今天的我",
    hint: "根据当下心情推荐",
  },
  {
    id: "identity",
    emoji: "🌟",
    label: "一直的我",
    hint: "基于我的品味画像",
  },
  {
    id: "novelty",
    emoji: "🎲",
    label: "想尝试的我",
    hint: "跳出舒适圈探索",
  },
];

interface SessionModeSelectorProps {
  value: SessionMode;
  onChange: (mode: SessionMode) => void;
  disabled?: boolean;
}

export function SessionModeSelector({
  value,
  onChange,
  disabled = false,
}: SessionModeSelectorProps) {
  return (
    <div className="flex items-center gap-1.5">
      {MODES.map((mode) => {
        const isActive = value === mode.id;
        return (
          <button
            key={mode.id}
            type="button"
            onClick={() => onChange(mode.id)}
            disabled={disabled}
            title={mode.hint}
            className={[
              "px-2.5 py-1 rounded-full text-xs font-medium transition-all duration-200",
              "border border-transparent",
              isActive
                ? "bg-stone-800 text-white shadow-sm"
                : "bg-white/80 text-stone-500 hover:text-stone-700 hover:bg-stone-100",
              disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer",
            ].join(" ")}
          >
            <span className="mr-1">{mode.emoji}</span>
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}
