export interface GuestSessionInput {
  emotion_card_ids: string[];
  scene_tag: string | null;
  browser_id?: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Record<string, unknown>;
  };
}

export interface HealthResponse {
  status: "ok" | "degraded";
  neo4j: boolean;
  postgres: boolean;
  redis: boolean;
}
