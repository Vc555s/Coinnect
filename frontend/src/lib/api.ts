// Typed client for the Coinnect API.

export type SkillKind = "offer" | "request";
export type ExchangeStatus = "pending" | "accepted" | "completed" | "declined" | "cancelled";

export interface Member {
  id: number;
  name: string;
  headline: string;
  location: string;
  trust: number;
  ratings: number;
  sessions_taught: number;
}

export interface Me extends Member {
  email: string;
  bio: string;
  balance: number;
  escrow: number;
  created_at: string;
}

export interface Skill {
  id: number;
  name: string;
  kind: SkillKind;
  category: string;
  level: string;
  description: string;
  rate: number;
  availability: string;
  created_at: string;
  owner: Member;
}

export interface Exchange {
  id: number;
  skill_id: number | null;
  skill_name: string;
  amount: number;
  message: string;
  status: ExchangeStatus;
  receipt_cid: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  provider: Member;
  learner: Member;
  role: "provider" | "learner" | "observer";
  ratings: { rater_id: number; ratee_id: number; score: number; comment: string }[];
}

export interface LedgerRecord {
  schema: string;
  seq: number;
  kind: string;
  prev: string | null;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface LedgerEntry {
  seq: number;
  cid: string;
  prev_cid: string | null;
  kind: "genesis" | "exchange" | "rating" | string;
  created_at: string;
  record: LedgerRecord;
  pinned: boolean;
  pin_error: string | null;
  gateway_url: string | null;
}

export interface LedgerDetail extends LedgerEntry {
  next_cid: string | null;
  verification: { cid: string; recomputed_cid: string; valid: boolean; hash_matches: boolean };
}

export interface ChainCheck {
  valid: boolean;
  length: number;
  checked: number;
  head?: string;
  broken_at: string | null;
  problem: string | null;
}

export interface Stats {
  members: number;
  offers: number;
  requests: number;
  sessions: number;
  coins_circulated: number;
  average_rating: number;
  receipts: number;
  top_offered: { name: string; count: number }[];
  top_wanted: { name: string; count: number }[];
  categories: { name: string; count: number }[];
}

export interface Matches {
  has_wants: boolean;
  has_offers: boolean;
  by_want: { want: Skill; offers: { score: number; skill: Skill }[] }[];
  swaps: { score: number; you_get: Skill; you_give: Skill; their_request: Skill }[];
}

export interface Profile {
  member: Member;
  bio: string;
  joined: string;
  skills: Skill[];
  reviews: { score: number; comment: string; skill: string; from: string; date: string }[];
  history: Exchange[];
}

export interface Signal {
  user_id: number;
  name: string;
  severity: "high" | "medium" | "low";
  signal: string;
  detail: string;
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
const TOKEN_KEY = "coinnect.token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function messageFrom(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = first.loc?.[first.loc.length - 1];
    const msg = (first.msg ?? fallback).replace(/^Value error, /, "");
    return field && typeof field === "string" ? `${field}: ${msg}` : msg;
  }
  return fallback;
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Can't reach the Coinnect server. Is the backend running?");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401) tokenStore.clear();
    throw new ApiError(res.status, messageFrom(data?.detail, `Request failed (${res.status})`));
  }
  return data as T;
}

export const rawUrl = (cid: string) => `${BASE}/api/ledger/${cid}/raw`;
