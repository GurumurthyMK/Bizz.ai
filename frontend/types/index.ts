/** Shared frontend types. Business entities arrive with their phases. */

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
}

export interface DbHealthResponse {
  status: string;
  database: string;
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface OverviewKpi {
  label: string;
  value: number;
  previous_value: number;
  change_pct: number | null;
  direction: "up" | "down" | "flat";
}

export interface OverviewHealth {
  revenue: OverviewKpi;
  active_customers: OverviewKpi;
  transactions: OverviewKpi;
  avg_order_value: OverviewKpi;
}

export interface OverviewTrendBucket {
  period_start: string;
  period_end: string;
  revenue: number;
  orders: number;
  active_customers: number;
  interactions: number;
}

export interface InvestigationLink {
  label: string;
  href: string;
  kind: "section" | "entity";
}

export interface AttentionItem {
  id: string;
  severity: "high" | "medium" | "low";
  title: string;
  description: string;
  affected_customers: number;
  metric_value: number | null;
  metric_label: string | null;
  links: InvestigationLink[];
}

export interface OpportunityItem {
  customer_id: number;
  score: number;
  tier: string;
  reasons: string[];
  links: InvestigationLink[];
}

export interface Alert {
  id: number;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  evidence: Record<string, unknown> | null;
  entity_type: string | null;
  entity_id: number | null;
  dedup_key: string;
  status: string;
  created_at: string;
  acknowledged_at: string | null;
}

export interface DetectionReport {
  reference_date: string;
  evaluated: number;
  created: number;
  skipped_duplicates: number;
}

export interface RecommendationItem {
  title: string;
  detail: string;
  priority: string;
}

export interface ReportNarrative {
  executive_summary: string | null;
  recommendations: string | null;
  model: string | null;
  provider: string | null;
}

export interface BusinessReport {
  meta: {
    reference_date: string;
    history_days: number;
    llm_available: boolean;
    customer_count: number;
  };
  executive_summary: string;
  key_metrics: OverviewHealth;
  customer_trends: OverviewTrendBucket[];
  segments: Segment[];
  predictions: {
    churn_high_count: number;
    purchase_high_count: number;
    top_churn: Prediction[];
    top_purchase: Prediction[];
  };
  opportunities: {
    total: number;
    high_count: number;
    top: Opportunity[];
  };
  recommendations: RecommendationItem[];
  narrative: ReportNarrative;
}

export type AIContextKind = "overview" | "customer" | "segment" | "opportunity";

export interface AIAnswer {
  text: string;
  model: string;
  provider: string;
  context_kind: string;
}

export interface OverviewMeta {
  reference_date: string;
  history_days: number;
  ml_available: boolean;
  customer_count: number;
}

export interface OverviewResponse {
  meta: OverviewMeta;
  health: OverviewHealth;
  trends: OverviewTrendBucket[];
  attention: AttentionItem[];
  opportunities: OpportunityItem[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Customer {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  city: string | null;
  country: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerMetrics {
  customer_id: number;
  total_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  refunded_orders: number;
  pending_orders: number;
  total_revenue: number;
  total_quantity: number;
  total_discount: number;
  avg_order_value: number;
  max_order_value: number;
  min_order_value: number;
  first_order_date: string | null;
  last_order_date: string | null;
  active_span_days: number;
  avg_days_between_orders: number;
  orders_last_30d: number;
  orders_last_90d: number;
  orders_last_180d: number;
  revenue_last_90d: number;
  revenue_prior_90d: number;
  order_trend_90d: number;
  revenue_trend_90d: number;
  distinct_products: number;
  distinct_categories: number;
  distinct_brands: number;
  favorite_category: string | null;
  favorite_category_share: number;
  refund_count: number;
  refund_rate: number;
  refunded_amount: number;
  total_interactions: number;
  distinct_interaction_types: number;
  interactions_last_30d: number;
  interactions_last_90d: number;
  interactions_prior_90d: number;
  interaction_trend_90d: number;
  purchase_interactions: number;
  browse_interactions: number;
  support_interactions: number;
  review_referral_interactions: number;
  campaign_linked_interactions: number;
  distinct_campaigns: number;
  last_interaction_date: string | null;
  days_since_last_interaction: number | null;
  recency_days: number | null;
  is_inactive_90d: boolean;
}

export interface Segment {
  id: number;
  cluster_id: number;
  name: string;
  size: number;
  share: number;
  avg_recency_days: number;
  avg_completed_orders: number;
  avg_revenue: number;
  silhouette: number | null;
  model_version: string;
  reference_date: string;
  created_at: string;
}

export interface Prediction {
  id: number;
  customer_id: number;
  prediction_type: string;
  probability: number;
  band: string;
  signals: string[] | null;
  model_version: string;
  reference_date: string;
  created_at: string;
}

export interface Opportunity {
  id: number;
  customer_id: number;
  segment_id: number | null;
  opportunity_type: string;
  score: number;
  tier: string;
  estimated_value: number;
  reasons: string[] | null;
  signals: Record<string, number> | null;
  recommended_action: string;
  model_version: string;
  reference_date: string;
  created_at: string;
}

export interface CustomerIntelligence {
  customer: Customer;
  metrics: CustomerMetrics;
  segment: Segment | null;
  predictions: Prediction[];
  opportunities: Opportunity[];
}

export interface Transaction {
  id: number;
  customer_id: number;
  product_id: number;
  quantity: number;
  unit_price: number;
  discount: number;
  total_amount: number;
  status: string;
  transaction_date: string;
  refunded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Interaction {
  id: number;
  customer_id: number;
  campaign_id: number | null;
  interaction_type: string;
  channel: string;
  occurred_at: string;
  summary: string | null;
  extra: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export type DataEntity = "customers" | "products" | "transactions" | "campaigns" | "interactions";

export interface ImportRowError {
  line: number;
  column: string;
  message: string;
}

export interface ImportPreview {
  entity: string;
  filename: string;
  columns: string[];
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  errors: ImportRowError[];
  errors_truncated: boolean;
  sample: Record<string, string>[];
}

export interface ImportResult {
  entity: string;
  filename: string;
  status: string;
  rows_total: number;
  rows_inserted: number;
  rows_failed: number;
  errors: ImportRowError[];
}

export interface ImportJob {
  id: number;
  entity: string;
  filename: string;
  rows_total: number;
  rows_valid: number;
  rows_inserted: number;
  rows_failed: number;
  status: string;
  error_summary: Record<string, unknown>[] | null;
  created_at: string;
}

export interface DataHealth {
  counts: Record<string, number>;
  missing_values: Record<string, number>;
  integrity: Record<string, number>;
  freshness: {
    transaction_date_min: string | null;
    transaction_date_max: string | null;
    last_interaction_at: string | null;
  };
  last_import: {
    entity: string;
    status: string;
    filename: string;
    rows_total: number;
    rows_inserted: number;
    rows_failed: number;
    created_at: string | null;
  } | null;
}
