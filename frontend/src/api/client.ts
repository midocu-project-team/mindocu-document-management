/**
 * Thin fetch wrappers around the mindocu backend API.
 *
 * The base URL comes from VITE_API_BASE_URL (falling back to the local backend).
 * Every non-2xx response is turned into an ApiError carrying the backend's
 * ``detail`` message so callers/UI can surface it directly.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
);

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** Read the backend's ``{detail}`` error body and throw an ApiError. */
async function raiseError(response: Response): Promise<never> {
  let detail = `${response.status} ${response.statusText}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') {
      detail = body.detail;
    }
  } catch {
    // Non-JSON error body: keep the status line.
  }
  throw new ApiError(response.status, detail);
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) return raiseError(response);
  return response.json() as Promise<T>;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) return raiseError(response);
  return response.json() as Promise<T>;
}

export async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) return raiseError(response);
  return response.json() as Promise<T>;
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method: 'POST', body: form });
  if (!response.ok) return raiseError(response);
  return response.json() as Promise<T>;
}

export async function del(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
  if (!response.ok) await raiseError(response);
}

/** Absolute URL of a document's stored PDF (consumed directly by react-pdf). */
export function pdfUrl(documentId: string): string {
  return `${API_BASE}/documents/${documentId}/pdf`;
}
