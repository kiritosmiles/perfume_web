export interface NotesPyramid {
  top: string[];
  middle: string[];
  base: string[];
}

export interface RecommendationSkeleton {
  rank: number;
  name: string;
  brand: string;
  notes_combination: NotesPyramid;
  match_score: number;
  source: "graphrag_match" | "template_fallback" | "llm_composer";
  allergen_warnings: string[];
  is_partial: true;
  image_url: string | null;
  fragrantica_url: string | null;
  longevity?: number;
  sillage?: number;
  season?: string;
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
