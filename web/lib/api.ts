"use client";

import { clearToken, getToken } from "./auth";

/**
 * Typed fetch wrapper for the Vestra FastAPI backend.
 *
 * Base URL comes from NEXT_PUBLIC_API_URL (defaults to localhost:8000). The
 * bearer token (when present) is attached automatically. A 401 clears the token
 * so the app can redirect to login.
 */
const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// --- Types mirroring the backend responses -------------------------------

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
}

export interface InvestorProfile {
  user_id: string;
  risk_tolerance: "conservative" | "moderate" | "aggressive";
  cash_balance: number;
  holdings: Record<string, number>;
  target_allocation: Record<string, number>;
}

export interface Exposure {
  cash_balance: number;
  total_positions: number;
  concentration_risk: string;
  largest_sector: string | null;
  largest_sector_exposure: number;
  sector_breakdown: Record<string, number>;
}

export interface PortfolioResponse {
  profile: InvestorProfile;
  exposure: Exposure;
}

export interface AuditLog {
  _id: string;
  user_id: string;
  agent_name: string;
  action: string;
  payload: Record<string, unknown>;
}

// --- Endpoint helpers ----------------------------------------------------

export const auth = {
  register: (email: string, password: string) =>
    api<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    api<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<{ user_id: string; email: string }>("/auth/me"),
};

export const portfolio = {
  get: () => api<PortfolioResponse>("/portfolio"),
};

export const audit = {
  list: (limit = 100) => api<{ logs: AuditLog[] }>(`/audit?limit=${limit}`),
};
