import { create } from "zustand";
import type { RecommendationSkeleton } from "@perfume/shared";

// Re-export shared type for consumers
export type SkeletonCard = RecommendationSkeleton;

export interface FragranceCardUI extends Omit<RecommendationSkeleton, "is_partial"> {
  expanded_fields?: Record<string, unknown>;
  copy_text: string;
  image_url: string | null;
  fragrantica_url: string | null;
}

type GenerationPhase =
  | "idle"
  | "skeleton"
  | "detail"
  | "copy"
  | "complete"
  | "error";

/** P0.1: Refinement tracking state — set by refine.start events */
export type RefineAttemptNumber = 1 | 2 | 3;
export type RefineMethod = "rule" | "semantic_gate" | "deep_upgrade";

interface GenerationState {
  generationId: string | null;
  phase: GenerationPhase;
  mode: "fast" | "deep" | null;
  cards: FragranceCardUI[];
  error: { code: string; user_message: string; degraded: boolean } | null;
  /** P0.1: Current refinement attempt (1-based, undefined when not refining) */
  refineAttempt: RefineAttemptNumber | null;
  /** P0.1: Method used for current/current refinement */
  refineMethod: RefineMethod | null;
  /** P0.1: True while a refine.* SSE round is in progress */
  isRefining: boolean;

  startGeneration: (id: string, mode: "fast" | "deep") => void;
  setSkeleton: (recs: RecommendationSkeleton[]) => void;
  addDetail: (rank: number, fields: Record<string, unknown>) => void;
  addCopyChunk: (rank: number, chunk: string) => void;
  completeGeneration: () => void;
  setError: (code: string, user_message: string, degraded: boolean) => void;
  reset: () => void;
  /** P0.1: Called by useSSE on refine.start */
  setRefineStart: (attempt: RefineAttemptNumber, method: RefineMethod) => void;
  /** P0.1: Called by useSSE on refine.result */
  setRefineResult: (adjustments: unknown[], updatedCards: unknown[]) => void;
  /** P0.1: Called by useSSE on refine.gate or refine.fallback */
  clearRefining: () => void;
}

const initialState = {
  generationId: null,
  phase: "idle" as const,
  mode: null,
  cards: [],
  error: null,
  refineAttempt: null,
  refineMethod: null,
  isRefining: false,
};

export const useGenerationStore = create<GenerationState>((set) => ({
  ...initialState,

  startGeneration: (id, mode) =>
    set({
      generationId: id,
      phase: "skeleton",
      mode,
      cards: [],
      error: null,
      refineAttempt: null,
      refineMethod: null,
      isRefining: false,
    }),

  setSkeleton: (recs) =>
    set({
      phase: "skeleton",
      cards: recs.map((r) => ({
        rank: r.rank,
        name: r.name,
        brand: r.brand,
        notes_combination: r.notes_combination,
        match_score: r.match_score,
        source: r.source,
        allergen_warnings: r.allergen_warnings,
        image_url: r.image_url || null,
        fragrantica_url: r.fragrantica_url || null,
        copy_text: "",
      })),
    }),

  addDetail: (rank, fields) =>
    set((state) => ({
      phase: "detail",
      cards: state.cards.map((c) =>
        c.rank === rank
          ? { ...c, expanded_fields: { ...c.expanded_fields, ...fields } }
          : c,
      ),
    })),

  addCopyChunk: (rank, chunk) =>
    set((state) => ({
      phase: "copy",
      cards: state.cards.map((c) =>
        c.rank === rank
          ? { ...c, copy_text: c.copy_text + chunk }
          : c,
      ),
    })),

  completeGeneration: () =>
    set({ phase: "complete", isRefining: false }),

  setError: (code, user_message, degraded) =>
    set({
      phase: "error",
      error: { code, user_message, degraded },
      isRefining: false,
    }),

  setRefineStart: (attempt, method) =>
    set({ refineAttempt: attempt, refineMethod: method, isRefining: true }),

  setRefineResult: (_adjustments, _updatedCards) =>
    set((state) => ({
      // Store the attempt metadata; actual card updates depend on refine.result event payload
      phase: "complete",
      isRefining: false,
    })),

  clearRefining: () =>
    set({ isRefining: false }),

  reset: () => set(initialState),
}));
