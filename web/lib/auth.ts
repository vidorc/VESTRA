"use client";

/**
 * Minimal JWT storage (localStorage). The token is set on login/register and
 * attached to every authenticated request by the api() helper. This is a
 * client-only module ("use client").
 */
const TOKEN_KEY = "vestra_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() != null;
}
