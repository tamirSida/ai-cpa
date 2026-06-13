import { auth } from "./firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

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
