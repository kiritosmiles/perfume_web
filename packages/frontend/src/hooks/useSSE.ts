import { useEffect, useRef } from "react";
import { createSSEConnection } from "../lib/sseClient";
import { useSessionStore } from "../stores/sessionStore";
import { useGenerationStore, type SkeletonCard } from "../stores/generationStore";

interface UseSSEOptions {
  url: string | null;
}

export function useSSE({ url }: UseSSEOptions) {
  const cleanupRef = useRef<(() => void) | null>(null);
  const setEmotion = useSessionStore((s) => s.setEmotion);
  const setSSEStatus = useSessionStore((s) => s.setSSEStatus);
  const setCrisis = useSessionStore((s) => s.setCrisis);

  const startGeneration = useGenerationStore((s) => s.startGeneration);
  const setSkeleton = useGenerationStore((s) => s.setSkeleton);
  const addDetail = useGenerationStore((s) => s.addDetail);
  const addCopyChunk = useGenerationStore((s) => s.addCopyChunk);
  const completeGeneration = useGenerationStore((s) => s.completeGeneration);
  const setError = useGenerationStore((s) => s.setError);

  useEffect(() => {
    if (!url) return;

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

          default:
            break;
        }
      },
      (status) => {
        setSSEStatus(status);
      },
    );

    cleanupRef.current = cleanup;
    return cleanup;
  }, [url, setEmotion, setSSEStatus, setCrisis, startGeneration, setSkeleton, addDetail, addCopyChunk, completeGeneration, setError]);

  const close = () => {
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
  };

  return { close };
}
