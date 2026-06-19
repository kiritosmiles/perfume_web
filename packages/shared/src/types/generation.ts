export interface RecommendationSkeleton {
  rank: number;
  name: string;
  brand: string;
  notes_combination: string[];
  match_score: number;
  source: "graphrag_match" | "template_fallback" | "llm_composer";
  allergen_warnings: string[];
  is_partial: true;
}

export interface FragranceCard extends Omit<RecommendationSkeleton, "is_partial"> {
  expanded_fields?: {
    graph_path?: string;
    longevity?: number;
    sillage?: number;
    season?: string;
    match_dimensions?: Record<string, number>;
  };
  copy_text: string;
}
