import { auth } from "./firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

// Tell the backend which language to localize its responses in (chat replies, errors).
// Reads the same localStorage key the i18n provider writes; defaults to English.
function langHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  return { "Accept-Language": localStorage.getItem("lang") === "he" ? "he" : "en" };
}

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit | undefined,
  forceRefresh: boolean
): Promise<T> {
  const user = auth.currentUser;
  if (!user) throw new ApiError("auth/no-user", "Not signed in", 401);
  const token = await user.getIdToken(forceRefresh);
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...langHeader(),
      ...init?.headers,
      Authorization: `Bearer ${token}`,
    },
  });
  // Note: init.body must not be a ReadableStream; FormData/string/Blob are safe to retry.
  if (res.status === 401 && !forceRefresh) return request<T>(path, init, true);
  if (res.status === 401) {
    await auth.signOut();
    window.location.assign("/login");
    throw new ApiError("auth/unauthorized", "Session expired", 401);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(
      body?.detail?.code ?? "api/error",
      body?.detail?.message ?? res.statusText,
      res.status
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function api<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, init, false);
}

export async function apiBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const user = auth.currentUser;
  if (!user) throw new ApiError("auth/no-user", "Not signed in", 401);
  const doFetch = async (force: boolean) => {
    const token = await user.getIdToken(force);
    return fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { ...langHeader(), ...(init.headers ?? {}), Authorization: `Bearer ${token}` },
    });
  };
  let res = await doFetch(false);
  if (res.status === 401) res = await doFetch(true);
  // Match request(): a persistent 401 means the session is dead — sign out and redirect.
  if (res.status === 401) {
    await auth.signOut();
    window.location.assign("/login");
    throw new ApiError("auth/unauthorized", "Session expired", 401);
  }
  // Match request(): surface the backend's structured error message, not a bare status code.
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(
      body?.detail?.code ?? "api/error",
      body?.detail?.message ?? res.statusText,
      res.status
    );
  }
  return res.blob();
}
