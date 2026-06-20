import { describe, it, expect, beforeEach } from "vitest";
import { useSessionStore } from "./sessionStore";

describe("sessionStore", () => {
  beforeEach(() => {
    useSessionStore.setState({
      sessionId: null,
      emotion: null,
      sseStatus: "idle",
      crisis: null,
    });
  });

  it("initializes with idle state", () => {
    const state = useSessionStore.getState();
    expect(state.sessionId).toBeNull();
    expect(state.emotion).toBeNull();
    expect(state.sseStatus).toBe("idle");
    expect(state.crisis).toBeNull();
  });

  it("setEmotion updates emotion state", () => {
    useSessionStore.getState().setEmotion({
      primary_emotion: "开心",
      confidence: 0.9,
      source: "card_preset",
      emotion_vector: { joy: 0.9, sadness: 0, anxiety: 0, calm: 0, excitement: 0, nostalgia: 0, romance: 0, melancholy: 0 },
    });
    const state = useSessionStore.getState();
    expect(state.emotion?.primary_emotion).toBe("开心");
    expect(state.emotion?.confidence).toBe(0.9);
  });

  it("setSSEStatus transitions states", () => {
    useSessionStore.getState().setSSEStatus("connecting");
    expect(useSessionStore.getState().sseStatus).toBe("connecting");
    useSessionStore.getState().setSSEStatus("active");
    expect(useSessionStore.getState().sseStatus).toBe("active");
  });

  it("reset clears all state", () => {
    useSessionStore.getState().setEmotion({
      primary_emotion: "平静",
      confidence: 0.8,
      source: "card_preset",
      emotion_vector: { joy: 0, sadness: 0, anxiety: 0, calm: 0.9, excitement: 0, nostalgia: 0, romance: 0, melancholy: 0 },
    });
    useSessionStore.getState().setSSEStatus("active");
    useSessionStore.getState().reset();

    const state = useSessionStore.getState();
    expect(state.sessionId).toBeNull();
    expect(state.emotion).toBeNull();
    expect(state.sseStatus).toBe("idle");
  });
});
