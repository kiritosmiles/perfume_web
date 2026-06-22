import { create } from "zustand";

interface EmotionState {
  emotion_vector: Record<string, number> | null;
  primary_emotion: string | null;
  confidence: number | null;
  source: "card_preset" | "bert" | "llm_fallback" | "llm_text" | null;
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

  setEmotion: (emotion: {
    emotion_vector: Record<string, number>;
    primary_emotion: string;
    confidence: number;
    source: string;
  }) => void;
  setSSEStatus: (status: SessionState["sseStatus"]) => void;
  setAck: (acked: boolean) => void;
  setRecall: (recall: SessionState["recall"]) => void;
  setCrisis: (crisis: SessionState["crisis"]) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  emotion: null,
  sseStatus: "idle" as const,
  crisis: null,
  messageAcked: false,
  recall: null,
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
      },
    }),

  setSSEStatus: (sseStatus) => set({ sseStatus }),

  setAck: (acked) => set({ messageAcked: acked }),

  setRecall: (recall) => set({ recall }),

  setCrisis: (crisis) => set({ crisis }),

  reset: () => set(initialState),
}));
