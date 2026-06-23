import type { SessionIntent } from "../../stores/sessionStore";

interface IntentSelectorProps {
  value: SessionIntent;
  onChange: (intent: SessionIntent) => void;
  disabled?: boolean;
  /** If true, gift/explore are locked (guest mode) */
  isGuest?: boolean;
}

const INTENTS: Array<{ id: SessionIntent; emoji: string; label: string; desc: string }> = [
  { id: "self_use", emoji: "👤", label: "为自己选", desc: "Self" },
  { id: "gift", emoji: "🎁", label: "送礼物", desc: "Gift" },
  { id: "explore", emoji: "🔍", label: "随便逛逛", desc: "Explore" },
];

export function IntentSelector({ value, onChange, disabled, isGuest }: IntentSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-stone-400 shrink-0">I'm</span>
      <div className="flex gap-1.5" role="radiogroup" aria-label="Select intent">
        {INTENTS.map((intent) => {
          const locked = isGuest && intent.id !== "self_use";
          const isActive = value === intent.id;
          return (
            <button
              key={intent.id}
              type="button"
              disabled={disabled || locked}
              onClick={() => onChange(intent.id)}
              className={[
                "inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200",
                "border",
                isActive
                  ? "bg-stone-800 text-stone-50 border-stone-800 shadow-glow"
                  : locked
                    ? "bg-stone-100 text-stone-300 border-stone-200 cursor-not-allowed opacity-50"
                    : "bg-white/60 text-stone-600 border-stone-200 hover:border-stone-400 hover:text-stone-800",
              ].join(" ")}
              title={locked ? "登录后可解锁此模式 (Login to unlock)" : intent.desc}
            >
              <span className="text-sm">{locked ? "🔒" : intent.emoji}</span>
              <span>{intent.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
