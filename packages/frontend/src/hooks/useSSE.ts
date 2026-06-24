import { useEffect, useRef } from "react";
import { createSSEConnection } from "../lib/sseClient";
import { useSessionStore } from "../stores/sessionStore";
import { useGenerationStore, type SkeletonCard } from "../stores/generationStore";

interface UseSSEOptions {
  url: string | null;
}

export function useSSE({ url }: UseSSEOptions) {
  const cleanupRef = useRef<(() => void) | null>(null);
  const lastUrlRef = useRef<string | null>(null);
  const setEmotion = useSessionStore((s) => s.setEmotion);
  const setSSEStatus = useSessionStore((s) => s.setSSEStatus);
  const setCrisis = useSessionStore((s) => s.setCrisis);
  const setAck = useSessionStore((s) => s.setAck);
  const setRecall = useSessionStore((s) => s.setRecall);
  const setIntent = useSessionStore((s) => s.setIntent);
  const setGate = useSessionStore((s) => s.setGate);

  const startGeneration = useGenerationStore((s) => s.startGeneration);
  const setSkeleton = useGenerationStore((s) => s.setSkeleton);
  const addDetail = useGenerationStore((s) => s.addDetail);
  const addCopyChunk = useGenerationStore((s) => s.addCopyChunk);
  const completeGeneration = useGenerationStore((s) => s.completeGeneration);
  const setError = useGenerationStore((s) => s.setError);

  useEffect(() => {
    // Reset URL tracking when url is cleared (e.g. handleReset)
    if (!url) {
      lastUrlRef.current = null;
      return;
    }

    // StrictMode dev guard: React 18 double-invokes effects in dev mode.
    // If we already connected to this exact URL, skip to avoid duplicate
    // backend calls (emotion resolution, GraphRAG, LLM copy generation).
    if (lastUrlRef.current === url) return;
    lastUrlRef.current = url;

    // Cleanup previous connection
    if (cleanupRef.current) {
      cleanupRef.current();
    }

    const cleanup = createSSEConnection(
      url,
      (_type, data) => {
        const type = _type as string;
        switch (type) {
          case "chat.emotion":
            setEmotion({
              emotion_vector: data.emotion_vector as Record<string, number>,
              primary_emotion: data.primary_emotion as string,
              confidence: data.confidence as number,
              source: data.source as string,
              value_dimensions: data.value_dimensions as Record<string, number> | undefined,
            });
            break;

          case "chat.ack":
            setAck(true);
            break;

          case "chat.intent":
            setIntent((data.intent as string) as "self_use" | "gift" | "explore" || "self_use");
            break;

          case "gate.check":
            setGate({
              verdict: (data.verdict as "sufficient" | "partial" | "insufficient"),
              questions: null,
              hint: null,
              bypassed: (data.bypassed as boolean) || false,
            });
            break;

          case "gate.ask":
            setGate({
              verdict: "insufficient",
              questions: (data.questions as string[]) || [],
              hint: (data.hint as string) || null,
              bypassed: false,
            });
            break;

          case "gate.wait":
            // Keep existing gate state but mark as waiting
            setGate({
              verdict: "partial",
              questions: null,
              hint: null,
              bypassed: false,
            });
            break;

          case "chat.recall":
            setRecall({
              complexity: data.complexity as string,
              recalled_count: data.recalled_count as number,
              memory_sources: (data.memory_sources as string[]) || [],
              latency_ms: data.latency_ms as number,
            });
            break;

          case "gen.start":
            startGeneration(
              data.generation_id as string,
              (data.mode as "fast" | "deep") || "fast",
            );
            break;

          case "gen.skeleton":
            setSkeleton(data.recommendations as SkeletonCard[]);
            break;

          case "gen.detail":
            addDetail(
              data.rank as number,
              (data.expanded_fields as Record<string, unknown>) || {},
            );
            break;

          case "gen.copy":
            addCopyChunk(data.rank as number, data.copy_text_chunk as string);
            break;

          case "gen.complete":
            completeGeneration();
            break;

          case "gen.error":
            setError(
              data.code as string,
              data.user_message as string,
              (data.degraded as boolean) || false,
            );
            break;

          case "safety.warn":
          case "safety.crisis":
          case "safety.block":
            setCrisis({
              is_crisis: true,
              severity: (data.level || data.severity || "medium") as string,
            });
            break;

          case "safety.ok":
            setCrisis(null);
            break;

          default:
            break;
        }
      },
      (status) => {
        setSSEStatus(status);
      },
    );

    cleanupRef.current = cleanup;
    return () => {
      cleanup();
      cleanupRef.current = null;
      // Note: do NOT reset lastUrlRef here — StrictMode dev calls
      // cleanup-then-remount with the same url; keeping lastUrlRef
      // prevents the remount from opening a second EventSource.
    };
  }, [url, setEmotion, setSSEStatus, setCrisis, setAck, setIntent, setRecall, setGate,
      startGeneration, setSkeleton, addDetail, addCopyChunk, completeGeneration, setError]);

  // Auto-close SSE connection when generation completes or errors
  // Prevents reconnect loop caused by server closing the one-shot stream
  const phase = useGenerationStore((s) => s.phase);
  useEffect(() => {
    if ((phase === "complete" || phase === "error") && cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
  }, [phase]);

  const close = () => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
  };

  return { close };
}
