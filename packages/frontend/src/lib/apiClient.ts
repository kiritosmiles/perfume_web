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
