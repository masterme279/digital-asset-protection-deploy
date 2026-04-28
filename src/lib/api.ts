export interface ApiError extends Error {
  status?: number;
  data?: unknown;
}

const DEFAULT_API_BASE = 'http://127.0.0.1:8000';

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || DEFAULT_API_BASE;

export function getStoredTokens(): { access: string; refresh: string } | null {
  try {
    const raw = localStorage.getItem('sentinel_tokens');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { access?: string; refresh?: string };
    if (!parsed.access || !parsed.refresh) return null;
    return { access: parsed.access, refresh: parsed.refresh };
  } catch {
    return null;
  }
}

export function storeTokens(tokens: { access: string; refresh: string } | null) {
  if (!tokens) {
    localStorage.removeItem('sentinel_tokens');
    return;
  }
  localStorage.setItem('sentinel_tokens', JSON.stringify(tokens));
}

function buildHeaders(isJson = true) {
  const headers: Record<string, string> = {};
  if (isJson) headers['Content-Type'] = 'application/json';
  const tokens = getStoredTokens();
  if (tokens?.access) headers.Authorization = `Bearer ${tokens.access}`;
  return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = new Error('API request failed') as ApiError;
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<T>(res);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    headers: buildHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers: buildHeaders(),
  });
  return handleResponse<T>(res);
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: buildHeaders(false),
    body: form,
  });
  return handleResponse<T>(res);
}
