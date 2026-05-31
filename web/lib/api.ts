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

// --- Phase 1/2/4 types ---------------------------------------------------

export interface HealthFactor {
  name: string;
  score: number;
  weight: number;
  note: string;
}

export interface PortfolioHealth {
  score: number;
  band: "poor" | "fair" | "good" | "excellent";
  factors: HealthFactor[];
}

export type RegimeType = "bull" | "bear" | "sideways" | "high_volatility" | "crisis";

export interface MarketRegime {
  regime: RegimeType;
  confidence: number;
  rationale: string;
}

export interface ScenarioOutcome {
  name: "best" | "base" | "worst";
  probability: number;
  expected_return_pct: number;
  portfolio_impact: number;
}

export interface SimulationResult {
  _id?: string;
  event_id?: string | null;
  ts?: string;
  scenarios: ScenarioOutcome[];
  expected_return_pct: number;
  expected_drawdown_pct: number;
  risk_score: number;
  upside_pct: number;
}

export interface RebalanceAction {
  ticker: string;
  action: "BUY" | "SELL";
  quantity: number;
  reason: string;
}

export interface RebalancePlan {
  drift_detected: boolean;
  actions: RebalanceAction[];
  notes: string;
}

export interface TradeDecision {
  action: "BUY" | "SELL" | "HOLD";
  ticker: string;
  quantity: number;
  reasoning: string;
}

export interface ConfidenceScore {
  decision_confidence: number;
  risk_confidence: number;
  data_completeness: number;
  overall: number;
}

export interface ApprovalRequest {
  _id: string;
  thread_id: string;
  user_id: string;
  event_id?: string | null;
  decision: TradeDecision;
  confidence?: ConfidenceScore | null;
  reflection?: Record<string, unknown> | null;
  status: "pending" | "approved" | "rejected";
  reason?: string | null;
  ts?: string;
}

export interface DigitalTwin {
  age?: number | null;
  annual_income: number;
  monthly_expenses: number;
  monthly_emi: number;
  monthly_sip: number;
  emergency_fund: number;
  tax_bracket: number;
  risk_profile: "conservative" | "moderate" | "aggressive";
}

export type GoalType =
  | "retirement"
  | "house"
  | "education"
  | "emergency_fund"
  | "wealth_growth";

export interface Goal {
  goal_id?: string;
  type: GoalType;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date?: string | null;
  priority: "low" | "medium" | "high";
}

// --- Phase 1/2/4 endpoint helpers ----------------------------------------

export const health = {
  get: () => api<PortfolioHealth>("/portfolio/health"),
};

export const market = {
  regime: () => api<MarketRegime>("/market/regime"),
};

export const simulations = {
  list: (limit = 50) =>
    api<{ simulations: SimulationResult[] }>(`/simulations?limit=${limit}`),
};

export const rebalance = {
  preview: (driftThresholdPct = 5) =>
    api<RebalancePlan>(`/rebalance/preview?drift_threshold_pct=${driftThresholdPct}`, {
      method: "POST",
    }),
};

export const approvals = {
  list: (status?: string) =>
    api<{ approvals: ApprovalRequest[] }>(
      `/approvals${status ? `?status=${status}` : ""}`,
    ),
  decide: (id: string, approved: boolean, reason?: string) =>
    api<{ approval_id: string; decision: string; result: unknown }>(
      `/approvals/${id}/decision`,
      { method: "POST", body: JSON.stringify({ approved, reason }) },
    ),
};

export const digitalTwin = {
  get: () => api<{ digital_twin: DigitalTwin | null }>("/digital-twin"),
  put: (twin: DigitalTwin) =>
    api<{ digital_twin: DigitalTwin }>("/digital-twin", {
      method: "PUT",
      body: JSON.stringify(twin),
    }),
};

export const goals = {
  list: () => api<{ goals: Goal[] }>("/goals"),
  create: (goal: Omit<Goal, "goal_id">) =>
    api<{ goal: Goal }>("/goals", { method: "POST", body: JSON.stringify(goal) }),
  update: (goalId: string, updates: Partial<Goal>) =>
    api<{ goal: Goal }>(`/goals/${goalId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    }),
  remove: (goalId: string) =>
    api<{ status: string; goal_id: string }>(`/goals/${goalId}`, {
      method: "DELETE",
    }),
};
