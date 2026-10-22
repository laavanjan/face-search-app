export type BoundingBox = { x: number; y: number; w: number; h: number };
export type FaceRecord = {
  face_id: string;
  photo_id: string;
  bbox: BoundingBox;
  det_score: number;
  quality: number;
};
export type UploadResponse = {
  photo_id: string;
  url: string;
  faces: FaceRecord[];
  review_status: string;
  message: string;
};
export type SearchMatch = {
  photo_id: string;
  face_id: string;
  url: string;
  score: number | null;
  bbox: BoundingBox;
  source: "model" | "human";
  reviewed_by?: string | null;
  confidence_band: "low" | "medium" | "high" | "human";
  band_meaning: string;
};
export type SearchCase = {
  case_id: string;
  status: string;
  query_faces: number;
  threshold_applied: number;
  candidate_count?: number | null;
  matches: SearchMatch[];
  notice: string;
  limitations?: string[];
  provenance?: Record<string, unknown> | null;
};
export type Health = {
  status: string;
  detector: string;
  model: string;
  storage: string;
  vector_store: string;
  indexing_paused: boolean;
  search_paused: boolean;
  config_approved: boolean;
  indexed_faces: number | null;
};
export type Me = { name: string; roles: string[]; permissions: string[] };
export type Policy = {
  legal_basis: string;
  consent_required: boolean;
  privacy_notice_url: string;
  privacy_notice_version: string;
  retention_days: Record<string, number>;
  appeal_sla_days: { acknowledge: number; resolve: number };
  human_review: { indexing_requires_approval: boolean; search_results_require_approval: boolean };
  search_min_threshold: number;
  search_max_limit: number;
  model: string;
  uses_aws: boolean;
};
export type GalleryItem = {
  photo_id: string;
  url: string;
  review_status: string;
  indexed_at: number;
  expires_at: number;
  face_count: number;
  quality: number;
};
export type PendingPhoto = {
  photo_id: string;
  review_status: string;
  indexed_at: number;
  uploaded_by: string;
  faces: { face_id: string; bbox: number[]; det_score: number; quality: number }[];
};
export type Candidate = {
  face_id: string;
  photo_id: string;
  score: number | null;
  bbox: number[];
  source: "model" | "human";
  decision: "pending" | "approve" | "reject";
  decided_by: string | null;
  reason: string | null;
};
export type ReviewCase = {
  id: string;
  created_at: number;
  requested_by: string;
  status: string;
  threshold: number;
  query_faces: number;
  has_query_image?: number;
  close_reason?: string | null;
  candidates?: Candidate[];
  undecided?: number;
};
export type AppealCategory =
  | "incorrect_match"
  | "indexing_objection"
  | "deletion_request"
  | "access_request"
  | "abuse_report"
  | "other";
export type Appeal = {
  id: string;
  created_at: number;
  category: AppealCategory;
  status: string;
  ack_by: number;
  resolve_by: number;
  outcome: string | null;
  resolution: string | null;
  resolved_at: number | null;
  photo_id?: string | null;
  case_id?: string | null;
  reason?: string;
  contact?: string | null;
  overdue?: boolean;
  photo_restricted?: boolean;
  access_token?: string;
};

// ---- auth -------------------------------------------------------------------
// The access key lives in sessionStorage (cleared when the tab closes) and is
// sent as a bearer token. The backend enforces every permission; the UI only
// hides controls a user cannot use.

const KEY = "fsa.accessKey";
export const AUTH_EVENT = "fsa-auth";

export function getAccessKey(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setAccessKey(k: string | null) {
  try {
    if (k) window.sessionStorage.setItem(KEY, k);
    else window.sessionStorage.removeItem(KEY);
  } catch {
    /* storage unavailable */
  }
  window.dispatchEvent(new Event(AUTH_EVENT));
}

async function call(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const k = getAccessKey();
  if (k) headers.set("Authorization", `Bearer ${k}`);
  const r = await fetch(`/api${path}`, { cache: "no-store", ...init, headers });
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const body = await r.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* not json */
    }
    if (r.status === 401) msg = "Sign in required. " + msg;
    throw new Error(msg);
  }
  return r;
}

const json = <T>(path: string, init?: RequestInit) => call(path, init).then((r) => r.json() as Promise<T>);
const post = <T>(path: string, body: unknown) =>
  json<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const whoami = () => json<Me>("/auth/me");
export const getPolicy = () => json<Policy>("/policy");
export const getHealth = () => json<Health>("/health");

export async function photoObjectUrl(photo_id: string): Promise<string> {
  const r = await call(`/photos/${photo_id}`);
  return URL.createObjectURL(await r.blob());
}

export async function caseQueryImageUrl(case_id: string): Promise<string> {
  const r = await call(`/review/cases/${case_id}/query-image`);
  return URL.createObjectURL(await r.blob());
}

// ---- index + search ---------------------------------------------------------

export function uploadPhoto(
  file: File,
  consent: boolean,
  minors: { present: boolean; guardianConsent: boolean } = { present: false, guardianConsent: false }
): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("consent", String(consent));
  fd.append("minors_present", String(minors.present));
  fd.append("guardian_consent", String(minors.guardianConsent));
  return json("/upload", { method: "POST", body: fd });
}

export function searchPhoto(
  file: File,
  {
    limit = 24,
    threshold = 0.35,
    consent = false,
    purpose,
  }: { limit?: number; threshold?: number; consent?: boolean; purpose: "self" | "consenting_person" }
): Promise<SearchCase> {
  const fd = new FormData();
  fd.append("purpose", purpose);
  fd.append("file", file);
  fd.append("limit", String(limit));
  fd.append("threshold", String(threshold));
  fd.append("consent", String(consent));
  return json("/search", { method: "POST", body: fd });
}

export const getSearchCase = (id: string) => json<SearchCase>(`/search/cases/${id}`);

export const getGallery = (status?: string) =>
  json<{ count: number; items: GalleryItem[] }>(`/gallery${status ? `?status=${status}` : ""}`);

export const deletePhoto = (photo_id: string, reason: string) =>
  json(`/photos/${photo_id}?reason=${encodeURIComponent(reason)}`, { method: "DELETE" });

// ---- review -----------------------------------------------------------------

export const pendingPhotos = () => json<{ items: PendingPhoto[] }>("/review/photos");
export const decidePhoto = (photo_id: string, decision: "approve" | "reject", reason: string) =>
  post(`/review/photos/${photo_id}`, { decision, reason });
export const listCases = (status: string) =>
  json<{ items: ReviewCase[] }>(`/review/cases?status=${encodeURIComponent(status)}`);
export const getCase = (id: string) => json<ReviewCase>(`/review/cases/${id}`);
export const decideCandidate = (
  id: string,
  face_id: string,
  decision: "approve" | "reject" | "reopen",
  reason: string,
  acknowledge_low_confidence = false
) =>
  post<ReviewCase>(`/review/cases/${id}/candidates/${encodeURIComponent(face_id)}`, {
    decision,
    reason,
    acknowledge_low_confidence,
  });
export const manualMatch = (id: string, photo_id: string, reason: string) =>
  post<ReviewCase>(`/review/cases/${id}/manual-match`, { photo_id, reason });
export const closeCase = (
  id: string,
  outcome: "completed" | "no_match" | "stopped" | "escalated",
  reason: string
) => post<ReviewCase>(`/review/cases/${id}/close`, { outcome, reason });
export const reopenCase = (id: string, reason: string) => post<ReviewCase>(`/review/cases/${id}/reopen`, { reason });

// ---- appeals ----------------------------------------------------------------

export const submitAppeal = (a: {
  category: AppealCategory;
  reason: string;
  photo_id?: string;
  face_id?: string;
  case_id?: string;
  contact?: string;
}) => post<Appeal>("/appeals", a);
export const getAppeal = (id: string, token: string) =>
  json<Appeal>(`/appeals/${id}`, { headers: { "X-Appeal-Token": token } });
export const listAppeals = () => json<{ items: Appeal[] }>("/appeals");
export const acknowledgeAppeal = (id: string) => post<Appeal>(`/appeals/${id}/acknowledge`, {});
export const resolveAppeal = (
  id: string,
  outcome: "upheld" | "partially_upheld" | "rejected",
  resolution: string,
  action: "none" | "delete_photo" | "restore_photo"
) => post<Appeal>(`/appeals/${id}/resolve`, { outcome, resolution, action });

// ---- support + transparency (public) ----------------------------------------

export type SupportRequest = {
  topic: "human_assistance" | "accessibility" | "language" | "cost" | "technical" | "other";
  message: string;
  preferred_format: "email" | "phone" | "large_print" | "easy_read" | "sign_language_interpreter" | "other";
  language: string;
  contact?: string;
};
export const submitSupport = (r: SupportRequest) => post<Appeal>("/support", r);
export const getTransparency = () => json<Record<string, unknown>>("/transparency-report");

// ---- admin ------------------------------------------------------------------

export type Controls = {
  indexing_paused: boolean;
  search_paused: boolean;
  config: {
    fingerprint: string;
    approved: boolean;
    last_approved_change_id: string | null;
    pending_diff: Record<string, { approved: unknown; running: unknown }>;
  };
};
export const getControls = () => json<Controls>("/admin/controls");
export const setControls = (c: { indexing_paused?: boolean; search_paused?: boolean; reason: string }) =>
  post<Controls>("/admin/controls", c);
export const approveConfig = (change_id: string, reason: string) =>
  post<Controls["config"]>("/admin/config/approve", { change_id, reason });
export const verifyAudit = () =>
  json<{ ok: boolean; rows: number; head?: string; first_bad_id?: number }>("/admin/audit/verify");
export const runRetention = () => post<Record<string, number>>("/admin/retention/run", {});
export const getAudit = (limit = 100) =>
  json<{ items: { id: number; ts: number; actor: string; roles: string; action: string; target: string | null; detail: Record<string, unknown> }[] }>(
    `/admin/audit?limit=${limit}`
  );

export const fmtDate = (ts: number | null | undefined) =>
  ts ? new Date(ts * 1000).toLocaleString() : "—";
export const fmtDay = (ts: number | null | undefined) =>
  ts ? new Date(ts * 1000).toLocaleDateString() : "—";
