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
    notes_combination?: string[];
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
