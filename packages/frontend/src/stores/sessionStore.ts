import { create } from "zustand";

interface EmotionState {
  emotion_vector: Record<string, number> | null;
  primary_emotion: string | null;
  confidence: number | null;
  source: "card_preset" | null;
}

interface SessionState {
  sessionId: string | null;
  emotion: EmotionState | null;
  sseStatus: "idle" | "connecting" | "active" | "retrying" | "disconnected";
  crisis: { is_crisis: boolean; severity: string } | null;

  setEmotion: (emotion: {
    emotion_vector: Record<string, number>;
    primary_emotion: string;
    confidence: number;
    source: string;
  }) => void;
  setSSEStatus: (status: SessionState["sseStatus"]) => void;
  setCrisis: (crisis: SessionState["crisis"]) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  emotion: null,
  sseStatus: "idle" as const,
  crisis: null,
};

export const useSessionStore = create<SessionState>((set) => ({
  ...initialState,

  setEmotion: (emotion) =>
    set({
      emotion: {
        emotion_vector: emotion.emotion_vector,
        primary_emotion: emotion.primary_emotion,
        confidence: emotion.confidence,
        source: emotion.source as "card_preset",
      },
    }),

  setSSEStatus: (sseStatus) => set({ sseStatus }),

  setCrisis: (crisis) => set({ crisis }),

  reset: () => set(initialState),
}));
