import { describe, it, expect, beforeEach } from "vitest";
import { useGenerationStore } from "./generationStore";

describe("generationStore", () => {
  beforeEach(() => {
    useGenerationStore.getState().reset();
  });

  it("initializes with idle state", () => {
    const state = useGenerationStore.getState();
    expect(state.phase).toBe("idle");
    expect(state.mode).toBeNull();
    expect(state.cards).toEqual([]);
    expect(state.error).toBeNull();
  });

  it("startGeneration sets phase to skeleton", () => {
    useGenerationStore.getState().startGeneration("gen-001", "fast");
    const state = useGenerationStore.getState();
    expect(state.generationId).toBe("gen-001");
    expect(state.phase).toBe("skeleton");
    expect(state.mode).toBe("fast");
  });

  it("setSkeleton populates cards", () => {
    useGenerationStore.getState().startGeneration("gen-002", "fast");
    useGenerationStore.getState().setSkeleton([
      {
        rank: 1,
        name: "No.5 Chanel",
        brand: "Chanel",
        notes_combination: { top: ["A"], middle: ["B"], base: ["C"] },
        match_score: 92,
        source: "graphrag_match" as const,
        allergen_warnings: [],
        is_partial: true as const,
        image_url: null,
        fragrantica_url: null,
      },
    ]);
    const state = useGenerationStore.getState();
    expect(state.phase).toBe("skeleton");
    expect(state.cards).toHaveLength(1);
    expect(state.cards[0].name).toBe("No.5 Chanel");
  });

  it("addDetail merges expanded_fields per rank", () => {
    useGenerationStore.getState().startGeneration("gen-003", "fast");
    useGenerationStore.getState().setSkeleton([
      {
        rank: 1,
        name: "Aventus",
        brand: "Creed",
        notes_combination: { top: ["X"], middle: ["Y"], base: ["Z"] },
        match_score: 88,
        source: "graphrag_match" as const,
        allergen_warnings: [],
        is_partial: true as const,
        image_url: null,
        fragrantica_url: null,
      },
    ]);
    useGenerationStore.getState().addDetail(1, {
      graph_path: "test",
      longevity: 6,
      sillage: 5,
      season: "all",
    });
    const state = useGenerationStore.getState();
    expect(state.cards[0].expanded_fields?.longevity).toBe(6);
  });

  it("addCopyChunk appends copy text", () => {
    useGenerationStore.getState().startGeneration("gen-004", "fast");
    useGenerationStore.getState().setSkeleton([
      {
        rank: 1,
        name: "Sauvage",
        brand: "Dior",
        notes_combination: { top: ["A"], middle: ["B"], base: ["C"] },
        match_score: 90,
        source: "graphrag_match" as const,
        allergen_warnings: [],
        is_partial: true as const,
        image_url: null,
        fragrantica_url: null,
      },
    ]);
    useGenerationStore.getState().addCopyChunk(1, "Hello");
    useGenerationStore.getState().addCopyChunk(1, " World");
    const state = useGenerationStore.getState();
    expect(state.cards[0].copy_text).toBe("Hello World");
  });

  it("completeGeneration sets phase to complete", () => {
    useGenerationStore.getState().startGeneration("gen-005", "fast");
    useGenerationStore.getState().completeGeneration();
    expect(useGenerationStore.getState().phase).toBe("complete");
  });

  it("reset clears all state", () => {
    useGenerationStore.getState().startGeneration("gen-006", "fast");
    useGenerationStore.getState().completeGeneration();
    useGenerationStore.getState().reset();
    const state = useGenerationStore.getState();
    expect(state.phase).toBe("idle");
    expect(state.cards).toEqual([]);
    expect(state.generationId).toBeNull();
  });
});
