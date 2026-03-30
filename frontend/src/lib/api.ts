const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string | null;
};

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method || "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error", code: "UNKNOWN" }));
    throw new ApiError(err.detail, err.code, res.status);
  }

  return res.json();
}

// --- Auth ---

export interface UserPublic {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export const auth = {
  register: (email: string, password: string, invite_code: string) =>
    request<{ token: string }>("/api/auth/register", { method: "POST", body: { email, password, invite_code } }),
  login: (email: string, password: string) =>
    request<{ token: string }>("/api/auth/token", { method: "POST", body: { email, password } }),
  me: (token: string) =>
    request<UserPublic>("/api/auth/me", { token }),
};

// --- Profile ---

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone_numbers: string[];
  email_addresses: string[];
  addresses: string[];
  city: string | null;
  state: string | null;
  age_range: string | null;
  relatives: string[];
  telegram_chat_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  full_name?: string;
  phone_numbers?: string[];
  email_addresses?: string[];
  addresses?: string[];
  city?: string;
  state?: string;
  age_range?: string;
  relatives?: string[];
  telegram_chat_id?: string;
}

export const profile = {
  get: (token: string) =>
    request<UserProfile>("/api/profile", { token }),
  update: (token: string, data: ProfileUpdate) =>
    request<UserProfile>("/api/profile", { method: "PUT", body: data, token }),
};

// --- Removals ---

export interface RemovalBatch {
  id: string;
  user_id: string;
  status: string;
  brokers_targeted: string[];
  brokers_completed: string[];
  brokers_failed: string[];
  total_removals: number;
  created_at: string;
  completed_at: string | null;
}

export interface RemovalRequest {
  id: string;
  user_id: string;
  batch_id: string | null;
  broker: string;
  status: string;
  method: string | null;
  opt_out_url: string | null;
  submitted_at: string | null;
  confirmed_at: string | null;
  recheck_after: string | null;
  attempts: number;
  last_error: string | null;
  notes: string | null;
  live_view_url: string | null;
  created_at: string;
}

export interface RemovalSummary {
  total: number;
  pending: number;
  in_progress: number;
  submitted: number;
  needs_verification: number;
  confirmed: number;
  failed: number;
}

export const removals = {
  create: (token: string, brokers: string[]) =>
    request<RemovalBatch>("/api/removals", { method: "POST", body: { brokers }, token }),
  list: (token: string) =>
    request<RemovalRequest[]>("/api/removals", { token }),
  batches: (token: string) =>
    request<RemovalBatch[]>("/api/removals/batches", { token }),
  batch: (token: string, id: string) =>
    request<RemovalBatch>(`/api/removals/batches/${id}`, { token }),
  summary: (token: string) =>
    request<RemovalSummary>("/api/removals/summary", { token }),
  get: (token: string, id: string) =>
    request<RemovalRequest>(`/api/removals/${id}`, { token }),
  recheck: (token: string, id: string) =>
    request<RemovalRequest>(`/api/removals/${id}/recheck`, { method: "POST", token }),
};

// --- Admin ---

export const admin = {
  bootstrap: (email: string, password: string, admin_secret: string) =>
    request<{ token: string }>("/api/admin/bootstrap", { method: "POST", body: { email, password, admin_secret } }),
  createInvite: (token: string, expires_in_days?: number) =>
    request<{ code: string }>("/api/admin/invites", { method: "POST", body: { expires_in_days }, token }),
  listInvites: (token: string) =>
    request<Array<{ code: string; created_by: string; used_by: string | null; is_used: boolean; expires_at: string | null }>>("/api/admin/invites", { token }),
};
