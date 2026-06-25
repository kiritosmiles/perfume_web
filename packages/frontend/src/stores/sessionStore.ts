import { create } from "zustand";

interface EmotionState {
  emotion_vector: Record<string, number> | null;
  primary_emotion: string | null;
  confidence: number | null;
  source: "card_preset" | "bert" | "llm_fallback" | "llm_text" | null;
  value_dimensions: Record<string, number> | null;
}

export type SessionIntent = "self_use" | "gift" | "explore";
export type SessionMode = "context" | "identity" | "novelty";

/** P0.2: Resume info from lifecycle.resume SSE event */
interface ResumeInfo {
  generation_id: string;
  from_phase: string;
  already_streamed_count: number;
}

/** P0.3: System notification entry from system.notification SSE event */
interface SystemNotification {
  kind: "perfumer_update" | "mood_journal_ready";
  message: string;
  action_link: string | null;
  ts: string;
}

interface SessionState {
  sessionId: string | null;
  emotion: EmotionState | null;
  sseStatus: "idle" | "connecting" | "active" | "retrying" | "disconnected";
  crisis: { is_crisis: boolean; severity: string } | null;
  messageAcked: boolean;
  recall: {
    complexity: string;
    recalled_count: number;
    memory_sources: string[];
    latency_ms: number;
  } | null;
  intent: SessionIntent;
  sessionMode: SessionMode;
  gate: {
    verdict: "sufficient" | "partial" | "insufficient" | null;
    questions: string[] | null;
    hint: string | null;
    bypassed: boolean;
  } | null;

  // --- P0.2: Lifecycle ---
  /** Active / idle_timeout / completed, set by lifecycle.session SSE event */
  sessionStatus: "active" | "idle_timeout" | "completed" | null;
  /** Resume info when reconnecting to an in-progress generation */
  resumeInfo: ResumeInfo | null;

  // --- P0.3: System notifications ---
  /** Queue of unread system notifications */
  notifications: SystemNotification[];
  /** Current system-level error (cleared on next event or user dismiss) */
  systemError: { code: string; user_message: string; retryable: boolean } | null;
  /** Dismiss system error */
  dismissSystemError: () => void;

  // --- P2.4: Chat-level error ---
  chatError: { code: string; user_message: string; retryable: boolean } | null;

  setEmotion: (emotion: {
    emotion_vector: Record<string, number>;
    primary_emotion: string;
    confidence: number;
    source: string;
    value_dimensions?: Record<string, number>;
  }) => void;
  setSSEStatus: (status: SessionState["sseStatus"]) => void;
  setAck: (acked: boolean) => void;
  setRecall: (recall: SessionState["recall"]) => void;
  setCrisis: (crisis: SessionState["crisis"]) => void;
  setIntent: (intent: SessionIntent) => void;
  setSessionMode: (mode: SessionMode) => void;
  setGate: (gate: SessionState["gate"]) => void;
  setSessionStatus: (status: "active" | "idle_timeout" | "completed") => void;
  setResumeInfo: (info: ResumeInfo | null) => void;
  pushNotification: (n: SystemNotification) => void;
  setSystemError: (e: { code: string; user_message: string; retryable: boolean } | null) => void;
  setChatError: (e: { code: string; user_message: string; retryable: boolean } | null) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  emotion: null,
  sseStatus: "idle" as const,
  crisis: null,
  messageAcked: false,
  recall: null,
  intent: "self_use" as SessionIntent,
  sessionMode: "context" as SessionMode,
  gate: null,
  sessionStatus: null,
  resumeInfo: null,
  notifications: [] as SystemNotification[],
  systemError: null,
  chatError: null,
};

export const useSessionStore = create<SessionState>((set) => ({
  ...initialState,

  setEmotion: (emotion) =>
    set({
      emotion: {
        emotion_vector: emotion.emotion_vector,
        primary_emotion: emotion.primary_emotion,
        confidence: emotion.confidence,
        source: emotion.source as EmotionState["source"],
        value_dimensions: emotion.value_dimensions || null,
      },
    }),

  setSSEStatus: (sseStatus) => set({ sseStatus }),

  setAck: (acked) => set({ messageAcked: acked }),

  setRecall: (recall) => set({ recall }),

  setCrisis: (crisis) => set({ crisis }),

  setIntent: (intent) => set({ intent }),

  setSessionMode: (sessionMode) => set({ sessionMode }),

  setGate: (gate) => set({ gate }),

  // P0.2
  setSessionStatus: (sessionStatus) => set({ sessionStatus }),

  setResumeInfo: (resumeInfo) => set({ resumeInfo }),

  // P0.3
  pushNotification: (n) =>
    set((state) => ({
      notifications: [...state.notifications, n].slice(-10), // keep last 10
    })),

  setSystemError: (systemError) => set({ systemError }),

  dismissSystemError: () => set({ systemError: null }),

  // P2.4
  setChatError: (chatError) => set({ chatError }),

  reset: () => set(initialState),
}));
