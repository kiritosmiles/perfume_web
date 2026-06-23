import { useEffect, useRef } from "react";
import { useGenerationStore } from "../stores/generationStore";
import { submitImplicitFeedback } from "../lib/apiClient";

/** Track implicit events: card dwell time, share clicks, refinement usage. */

interface ImplicitEvent {
  event_name: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export function useImplicitTracking() {
  const pendingRef = useRef<ImplicitEvent[]>([]);
  const generationIdRef = useRef<string | null>(null);
  const sentRef = useRef(false);

  const track = (eventName: string, payload: Record<string, unknown> = {}) => {
    pendingRef.current.push({
      event_name: eventName,
      payload,
      timestamp: new Date().toISOString(),
    });
  };

  const flush = () => {
    if (sentRef.current || pendingRef.current.length === 0) return;
    sentRef.current = true;
    const events = pendingRef.current.splice(0);
    submitImplicitFeedback(events, generationIdRef.current).catch(() => {
      // Silent fail — feedback is non-critical
    });
  };

  // Watch for gen.start to capture generation_id
  useEffect(() => {
    const unsub = useGenerationStore.subscribe((state, prev) => {
      // Reset tracking on new generation
      if (state.generationId && state.generationId !== prev.generationId) {
        generationIdRef.current = state.generationId;
        pendingRef.current = [];
        sentRef.current = false;
      }

      // Auto-track card_viewed when skeleton cards appear
      if (
        state.phase === "skeleton" &&
        prev.phase !== "skeleton" &&
        state.cards.length > 0
      ) {
        for (const card of state.cards) {
          pendingRef.current.push({
            event_name: "card_viewed",
            payload: { card_rank: card.rank, card_name: card.name },
            timestamp: new Date().toISOString(),
          });
        }
      }

      // Flush on gen.complete or gen.error
      if (
        (state.phase === "complete" || state.phase === "error") &&
        prev.phase !== "complete" &&
        prev.phase !== "error"
      ) {
        flush();
      }
    });

    return unsub;
  }, []);

  return { track, flush };
}
