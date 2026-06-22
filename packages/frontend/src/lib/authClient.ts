const BASE_URL = "/api/v1";

export interface AuthTokens {
  user: { id: string; email: string };
  access_token: string;
  refresh_token: string;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function register(email: string, password: string, browserId?: string): Promise<AuthTokens> {
  return apiPost<AuthTokens>("/auth/register", { email, password, browser_id: browserId || undefined });
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  return apiPost<AuthTokens>("/auth/login", { email, password });
}

export async function refreshToken(token: string): Promise<AuthTokens> {
  return apiPost<AuthTokens>("/auth/refresh", { refresh_token: token });
}
