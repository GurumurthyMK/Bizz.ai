import type {
  AIAnswer,
  AIContextKind,
  Alert,
  AuthResponse,
  BusinessReport,
  Customer,
  CustomerIntelligence,
  DataEntity,
  DataHealth,
  DbHealthResponse,
  DetectionReport,
  HealthResponse,
  ImportJob,
  ImportPreview,
  ImportResult,
  Interaction,
  Opportunity,
  OverviewResponse,
  Page,
  Prediction,
  Segment,
  Transaction,
  User,
} from "@/types";

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

/** Base URL of the FastAPI backend (no trailing slash). */
export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return trimTrailingSlash(raw);
}

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, detail: string, details?: unknown) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    // Session cookie (HttpOnly) must travel with every backend call.
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  return parseApiResponse<T>(response);
}

/** Shared response handling: string details, structured 422 payloads, no leaks. */
export async function parseApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    let details: unknown;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.length > 0) {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        details = body.detail;
        const first = body.detail[0] as Record<string, unknown> | undefined;
        if (first !== undefined && "line" in first && "message" in first) {
          detail = `${body.detail.length} row${body.detail.length === 1 ? "" : "s"} need attention before import.`;
        } else {
          const loc = first?.loc;
          const where =
            Array.isArray(loc) && loc.length > 0 ? ` (${String(loc[loc.length - 1])})` : "";
          detail =
            typeof first?.msg === "string"
              ? `Invalid file${where}: ${first.msg}`
              : `Invalid file (${response.status})`;
        }
      }
    } catch {
      // Fall through to the generic message; never surface parse internals.
    }
    throw new ApiError(response.status, detail, details);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Backend liveness probe (no database access). */
export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health", { signal });
}

/** Database connectivity verification via the backend. */
export function getDbHealth(signal?: AbortSignal): Promise<DbHealthResponse> {
  return request<DbHealthResponse>("/api/v1/health/db", { signal });
}

export interface AuthCredentials {
  email: string;
  password: string;
}

/** Register a new account. Sets the session cookie on success. */
export function registerUser(credentials: AuthCredentials): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** Log in. Sets the session cookie on success. */
export function loginUser(credentials: AuthCredentials): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

/** Log out. Clears the session cookie. */
export function logoutUser(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/v1/auth/logout", { method: "POST" });
}

/** Current session user. Throws ApiError(401) when unauthenticated. */
export function getCurrentUser(): Promise<User> {
  return request<User>("/api/v1/auth/me", { cache: "no-store" });
}

/** Business-health overview. All metrics come from the backend. */
export function getOverview(signal?: AbortSignal): Promise<OverviewResponse> {
  return request<OverviewResponse>("/api/v1/overview", {
    signal,
    cache: "no-store",
  });
}

function buildQuery(params: object): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const text = query.toString();
  return text ? `?${text}` : "";
}

/** Backend Decimals arrive as JSON strings; coerce once at the boundary. */
function toTransaction(raw: Transaction): Transaction {
  return {
    ...raw,
    unit_price: Number(raw.unit_price),
    discount: Number(raw.discount),
    total_amount: Number(raw.total_amount),
  };
}

function toOpportunity(raw: Opportunity): Opportunity {
  return { ...raw, estimated_value: Number(raw.estimated_value) };
}

export interface CustomerListParams {
  page?: number;
  page_size?: number;
  search?: string;
  city?: string;
  country?: string;
  sort_by?: "id" | "first_name" | "last_name" | "email" | "created_at";
  order?: "asc" | "desc";
}

export function listCustomers(
  params: CustomerListParams = {},
  signal?: AbortSignal,
): Promise<Page<Customer>> {
  return request<Page<Customer>>(`/api/v1/customers${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  });
}

export function getCustomerIntelligence(
  id: number,
  signal?: AbortSignal,
): Promise<CustomerIntelligence> {
  return request<CustomerIntelligence>(`/api/v1/customers/${id}/intelligence`, {
    signal,
    cache: "no-store",
  }).then((data) => ({
    ...data,
    opportunities: data.opportunities.map(toOpportunity),
  }));
}

export interface TransactionListParams {
  page?: number;
  page_size?: number;
  customer_id?: number;
  status?: string;
  sort_by?: "transaction_date" | "total_amount" | "id";
  order?: "asc" | "desc";
}

export function listTransactions(
  params: TransactionListParams = {},
  signal?: AbortSignal,
): Promise<Page<Transaction>> {
  return request<Page<Transaction>>(`/api/v1/transactions${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  }).then((page) => ({ ...page, items: page.items.map(toTransaction) }));
}

export function listInteractions(
  params: { page?: number; page_size?: number; customer_id?: number } = {},
  signal?: AbortSignal,
): Promise<Page<Interaction>> {
  return request<Page<Interaction>>(`/api/v1/interactions${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  });
}

export function listSegments(signal?: AbortSignal): Promise<Segment[]> {
  return request<Segment[]>("/api/v1/segments", { signal, cache: "no-store" });
}

export function getSegment(id: number, signal?: AbortSignal): Promise<Segment> {
  return request<Segment>(`/api/v1/segments/${id}`, { signal, cache: "no-store" });
}

export function listSegmentCustomers(
  id: number,
  params: { page?: number; page_size?: number } = {},
  signal?: AbortSignal,
): Promise<Page<Customer>> {
  return request<Page<Customer>>(`/api/v1/segments/${id}/customers${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  });
}

export interface PredictionListParams {
  page?: number;
  page_size?: number;
  prediction_type?: "churn" | "purchase";
  band?: string;
  customer_id?: number;
  min_probability?: number;
  sort_by?: "probability" | "customer_id";
  order?: "asc" | "desc";
}

export function listPredictions(
  params: PredictionListParams = {},
  signal?: AbortSignal,
): Promise<Page<Prediction>> {
  return request<Page<Prediction>>(`/api/v1/predictions${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  });
}

export interface OpportunityListParams {
  page?: number;
  page_size?: number;
  tier?: string;
  opportunity_type?: string;
  customer_id?: number;
  segment_id?: number;
  min_score?: number;
  sort_by?: "score" | "estimated_value" | "customer_id";
  order?: "asc" | "desc";
}

export function listOpportunities(
  params: OpportunityListParams = {},
  signal?: AbortSignal,
): Promise<Page<Opportunity>> {
  return request<Page<Opportunity>>(`/api/v1/opportunities${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  }).then((page) => ({ ...page, items: page.items.map(toOpportunity) }));
}

export function getOpportunity(id: number, signal?: AbortSignal): Promise<Opportunity> {
  return request<Opportunity>(`/api/v1/opportunities/${id}`, {
    signal,
    cache: "no-store",
  }).then(toOpportunity);
}

export interface AIContextRef {
  kind: AIContextKind;
  id?: number;
}

function aiBody(context: AIContextRef, extra?: { question?: string }) {
  return {
    method: "POST",
    body: JSON.stringify({ context, ...extra }),
  };
}

/** Grounded explanation of an entity's verified backend data. */
export function postAIInsight(
  context: AIContextRef,
  signal?: AbortSignal,
): Promise<AIAnswer> {
  return request<AIAnswer>("/api/v1/ai/insight", { ...aiBody(context), signal });
}

/** Answer an analytical question using only the entity's verified context. */
export function postAIAsk(
  context: AIContextRef,
  question: string,
  signal?: AbortSignal,
): Promise<AIAnswer> {
  return request<AIAnswer>("/api/v1/ai/ask", { ...aiBody(context, { question }), signal });
}

/** Concise summary of an entity's verified backend data. */
export function postAISummarize(
  context: AIContextRef,
  signal?: AbortSignal,
): Promise<AIAnswer> {
  return request<AIAnswer>("/api/v1/ai/summarize", { ...aiBody(context), signal });
}

export function previewCsvImport(
  entity: DataEntity,
  file: File,
  signal?: AbortSignal,
): Promise<ImportPreview> {
  const form = new FormData();
  form.append("file", file, file.name);
  return fetch(`${getApiBaseUrl()}/api/v1/data/preview?entity=${entity}`, {
    method: "POST",
    body: form,
    credentials: "include",
    signal,
  }).then(parseApiResponse<ImportPreview>);
}

export function importCsv(
  entity: DataEntity,
  file: File,
  signal?: AbortSignal,
): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file, file.name);
  return fetch(`${getApiBaseUrl()}/api/v1/data/import?entity=${entity}`, {
    method: "POST",
    body: form,
    credentials: "include",
    signal,
  }).then(parseApiResponse<ImportResult>);
}

export function getDataHealth(signal?: AbortSignal): Promise<DataHealth> {
  return request<DataHealth>("/api/v1/data/health", { signal, cache: "no-store" });
}

export function listImportJobs(signal?: AbortSignal): Promise<Page<ImportJob>> {
  return request<Page<ImportJob>>("/api/v1/data/imports?page_size=10", {
    signal,
    cache: "no-store",
  });
}

export interface AlertListParams {
  page?: number;
  page_size?: number;
  alert_type?: string;
  severity?: string;
  status?: string;
  entity_type?: string;
}

export function listAlerts(
  params: AlertListParams = {},
  signal?: AbortSignal,
): Promise<Page<Alert>> {
  return request<Page<Alert>>(`/api/v1/alerts${buildQuery(params)}`, {
    signal,
    cache: "no-store",
  });
}

export function detectAlerts(signal?: AbortSignal): Promise<DetectionReport> {
  return request<DetectionReport>("/api/v1/alerts/detect", {
    method: "POST",
    signal,
    cache: "no-store",
  });
}

export function acknowledgeAlert(id: number, signal?: AbortSignal): Promise<Alert> {
  return request<Alert>(`/api/v1/alerts/${id}/acknowledge`, {
    method: "PATCH",
    signal,
  });
}

export function generateReport(signal?: AbortSignal): Promise<BusinessReport> {
  return request<BusinessReport>("/api/v1/reports/generate", {
    method: "POST",
    signal,
    cache: "no-store",
  }).then((report) => ({
    ...report,
    opportunities: {
      ...report.opportunities,
      top: report.opportunities.top.map(toOpportunity),
    },
  }));
}
