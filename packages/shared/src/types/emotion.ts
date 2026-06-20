export interface EmotionVector {
  joy: number; sadness: number; anxiety: number; calm: number;
  excitement: number; nostalgia: number; romance: number; melancholy: number;
}

export interface EmotionCardDefinition {
  id: number; emoji: string; label: string; vector: EmotionVector;
}

export interface EmotionResult {
  emotion_vector: EmotionVector;
  primary_emotion: string;
  confidence: number;
  source: "card_preset" | "bert" | "llm_fallback" | "llm_text";
}

export interface SceneTag {
  id: number; emoji: string; label: string;
}
