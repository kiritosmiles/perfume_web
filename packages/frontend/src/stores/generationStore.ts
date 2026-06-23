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

interface GenerationState {
  generationId: string | null;
  phase: GenerationPhase;
  mode: "fast" | "deep" | null;
  cards: FragranceCardUI[];
  error: { code: string; user_message: string; degraded: boolean } | null;

  startGeneration: (id: string, mode: "fast" | "deep") => void;
  setSkeleton: (recs: RecommendationSkeleton[]) => void;
  addDetail: (rank: number, fields: Record<string, unknown>) => void;
  addCopyChunk: (rank: number, chunk: string) => void;
  completeGeneration: () => void;
  setError: (code: string, user_message: string, degraded: boolean) => void;
  reset: () => void;
}

const initialState = {
  generationId: null,
  phase: "idle" as const,
  mode: null,
  cards: [],
  error: null,
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
    set({ phase: "complete" }),

  setError: (code, user_message, degraded) =>
    set({
      phase: "error",
      error: { code, user_message, degraded },
    }),

  reset: () => set(initialState),
}));
