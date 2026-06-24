const BASE_URL = "/api/v1";

export class ApiClientError extends Error {
  code: string;
  retryable: boolean;
  details?: Record<string, unknown>;

  constructor(
    code: string,
    message: string,
    retryable: boolean,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.retryable = retryable;
    this.details = details;
  }
}

export async function apiPost<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    try {
      const errorData = await response.json();
      const err = errorData?.error || errorData;
      throw new ApiClientError(
        err?.code || "UNKNOWN_ERROR",
        err?.message || `Request failed with status ${response.status}`,
        err?.retryable ?? false,
        err?.details,
      );
    } catch (e) {
      if (e instanceof ApiClientError) throw e;
      throw new ApiClientError(
        "NETWORK_ERROR",
        `Request failed with status ${response.status}`,
        true,
      );
    }
  }

  return response.json() as Promise<T>;
}

export interface SharePayloadData {
  recommendations: Array<{
    rank: number;
    name: string;
    brand: string;
    notes_combination?: { top?: string[]; middle?: string[]; base?: string[] };
    match_score: number;
    copy_text?: string;
  }>;
  emotion: {
    primary_emotion: string;
    confidence: number;
    emotion_vector?: Record<string, number>;
  };
  scene_tag?: string | null;
  generation_id?: string | null;
}

export interface ShareCreateResponse {
  share_id: string;
  share_url: string;
}

export interface ShareDetailResponse {
  share_id: string;
  payload: SharePayloadData;
  created_at: string | null;
  expires_at: string | null;
}

export async function createShareLink(input: {
  recommendations: Array<Record<string, unknown>>;
  emotion: Record<string, unknown>;
  scene_tag?: string | null;
  generation_id?: string | null;
}): Promise<ShareCreateResponse> {
  return apiPost<ShareCreateResponse>("/share", input);
}

export async function getShareDetail(shareId: string): Promise<ShareDetailResponse> {
  return apiGet<ShareDetailResponse>(`/share/${shareId}`);
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);

  if (!response.ok) {
    try {
      const errorData = await response.json();
      const err = errorData?.error || errorData;
      throw new ApiClientError(
        err?.code || "UNKNOWN_ERROR",
        err?.message || `Request failed with status ${response.status}`,
        err?.retryable ?? false,
        err?.details,
      );
    } catch (e) {
      if (e instanceof ApiClientError) throw e;
      throw new ApiClientError(
        "NETWORK_ERROR",
        `Request failed with status ${response.status}`,
        true,
      );
    }
  }

  return response.json() as Promise<T>;
}

export interface LLMKeyInput {
  browser_id: string;
  api_key: string;
  base_url?: string | null;
}

export interface LLMKeyStatus {
  configured: boolean;
}

export async function saveLLMKey(input: LLMKeyInput): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/config/llm-key", input);
}

export async function getLLMKeyStatus(browserId: string): Promise<LLMKeyStatus> {
  return apiGet<LLMKeyStatus>(`/config/llm-key/status?browser_id=${encodeURIComponent(browserId)}`);
}

export function getBrowserId(): string {
  const key = "perfume_browser_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export interface MemoryTimelineItem {
  level: "L2" | "L3";
  id: string;
  text: string;
  emotion_profile?: Record<string, unknown>;
  created_at: string | null;
  metadata?: Record<string, unknown>;
}

export interface MemoryTimelineResponse {
  items: MemoryTimelineItem[];
  stats: { l1_count: number; l2_count: number; l3_count: number };
  total: number;
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export interface ExplicitFeedbackInput {
  generation_id: string;
  card_rank: number;
  reaction: "like" | "dislike";
  reason?: string;
}

export async function submitFeedback(input: ExplicitFeedbackInput): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Browser-Id": getBrowserId(),
  };
  // Add auth token if available
  const token = localStorage.getItem("access_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;

  await fetch(`${BASE_URL}/feedback/explicit`, {
    method: "POST",
    headers,
    body: JSON.stringify(input),
  });
}

export async function submitImplicitFeedback(
  events: Array<{ event_name: string; payload?: Record<string, unknown>; timestamp?: string }>,
  generationId?: string | null,
): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Browser-Id": getBrowserId(),
  };
  const token = localStorage.getItem("access_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const body: Record<string, unknown> = { events };
  if (generationId) body.generation_id = generationId;

  await fetch(`${BASE_URL}/feedback/implicit`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}

// ── Profile ────────────────────────────────────────────────────────────────────

export interface ProfileResponse {
  user_id: string;
  profile: Record<string, unknown> | null;
  conversation_count: number;
  updated_at: string | null;
  value_dimensions?: Record<string, number> | null;
}

export interface OnboardingAnswer {
  question: number;
  option: string;
  mapped_vector: Record<string, number> | null;
  mapped_tags: string[] | null;
}

export async function getProfile(): Promise<ProfileResponse> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${BASE_URL}/profile`, { headers });
  if (!resp.ok) {
    throw new ApiClientError("FETCH_ERROR", `Failed to fetch profile: ${resp.status}`, true);
  }
  return resp.json();
}

export async function submitOnboarding(
  answers: OnboardingAnswer[],
): Promise<{ user_id: string; profile: Record<string, unknown> }> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${BASE_URL}/profile/onboarding`, {
    method: "POST",
    headers,
    body: JSON.stringify({ answers }),
  });
  if (!resp.ok) {
    throw new ApiClientError("FETCH_ERROR", `Failed to submit onboarding: ${resp.status}`, true);
  }
  return resp.json();
}

// ── Journal ────────────────────────────────────────────────────────────────────

export interface EmotionTrendPoint {
  date: string;
  primary_emotion: string | null;
  emotion_scores: Record<string, number>;
  keywords: string[];
  summary_text: string;
}

export interface EmotionTrendResponse {
  user_id: string;
  days: number;
  count: number;
  data: EmotionTrendPoint[];
}

export interface WeeklyJournalResponse {
  user_id: string;
  week_start: string;
  week_end: string;
  this_week: {
    primary_emotion: string | null;
    emotion_vector: Record<string, number>;
    top_keywords: string[];
    session_count: number;
    days: Array<{ date: string; primary_emotion: string | null }>;
  } | null;
  last_week: {
    primary_emotion: string | null;
    emotion_vector: Record<string, number>;
    top_keywords: string[];
    session_count: number;
    days: Array<{ date: string; primary_emotion: string | null }>;
  } | null;
  narrative: string;
}

export async function getEmotionTrend(days = 30): Promise<EmotionTrendResponse> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`${BASE_URL}/journal/trend?days=${days}`, { headers });
  if (!resp.ok) {
    throw new ApiClientError("FETCH_ERROR", `Failed to fetch emotion trend: ${resp.status}`, true);
  }
  return resp.json();
}

export async function getWeeklyJournal(weekStart?: string): Promise<WeeklyJournalResponse> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const params = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : "";
  const resp = await fetch(`${BASE_URL}/journal/weekly${params}`, { headers });
  if (!resp.ok) {
    throw new ApiClientError("FETCH_ERROR", `Failed to fetch weekly journal: ${resp.status}`, true);
  }
  return resp.json();
}

export async function getMemoryTimeline(
  limit = 20,
  offset = 0,
  sessionId?: string,
): Promise<MemoryTimelineResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (sessionId) params.set("session_id", sessionId);

  const token = localStorage.getItem("access_token");
  const browserId = getBrowserId();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  else headers["X-Browser-Id"] = browserId;

  const resp = await fetch(`${BASE_URL}/memory/timeline?${params}`, { headers });
  if (!resp.ok) {
    throw new ApiClientError("FETCH_ERROR", `Failed to fetch memory timeline: ${resp.status}`, true);
  }
  return resp.json();
}
