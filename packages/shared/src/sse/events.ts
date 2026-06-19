import type { EmotionResult, RecommendationSkeleton } from "../types";

export type SSEEvent =
  | { type: "chat.ack"; message_id: string; server_ts: string }
  | { type: "chat.emotion"; emotion_vector: Record<string, number>; primary_emotion: string; confidence: number; source: EmotionResult["source"] }
  | { type: "gen.start"; generation_id: string; mode: "fast" | "deep" }
  | { type: "gen.skeleton"; generation_id: string; recommendations: RecommendationSkeleton[]; is_partial: true }
  | { type: "gen.detail"; generation_id: string; rank: number; expanded_fields: Record<string, unknown> }
  | { type: "gen.copy"; generation_id: string; rank: number; copy_text_chunk: string; is_final: boolean }
  | { type: "gen.complete"; generation_id: string; total_cards: number; metadata?: Record<string, unknown> }
  | { type: "gen.error"; generation_id?: string; code: string; user_message: string; degraded: boolean }
  | { type: "chat.intent"; intent: string; confidence: number }
  | { type: "chat.error"; code: string; user_message: string; retryable: boolean }
  | { type: "gate.check"; verdict: "sufficient" | "partial" | "insufficient"; latency_ms: number; bypassed: boolean }
  | { type: "gate.ask"; questions: string[]; hint: string }
  | { type: "gate.wait"; message: string }
  | { type: "refine.start"; attempt: 1 | 2 | 3; method: "rule" | "semantic_gate" }
  | { type: "refine.result"; adjustments: unknown[]; updated_cards: unknown[] }
  | { type: "refine.gate"; verdict: "continue" | "downgrade_to_ask"; reason: string }
  | { type: "refine.fallback"; message: string; action: "ask" | "upgrade_to_deep" }
  | { type: "safety.warn"; level: "low" | "medium"; message: string }
  | { type: "safety.crisis"; severity: "medium" | "high"; message: string; hotlines: Array<{ name: string; phone: string; region: string }> }
  | { type: "safety.block"; reason: string; user_message: string }
  | { type: "lifecycle.session"; status: "active" | "idle_timeout" | "completed"; session_id: string }
  | { type: "lifecycle.resume"; generation_id: string; from_phase: string; already_streamed_count: number }
  | { type: "system.heartbeat"; ts: string }
  | { type: "system.notification"; kind: string; message: string; action_link?: string }
  | { type: "system.error"; code: string; user_message: string; retryable: boolean };
