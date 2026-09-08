export type UserRole = 'store_manager' | 'regional_director' | 'hq' | 'admin';

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  store_nbr: number | null;
  is_active: boolean;
  created_at: string;
}

export interface SeriesRef {
  product_id: string;
  store_nbr: number;
  family: string;
}

export interface ForecastPoint {
  forecast_date: string;
  p10: number;
  p50: number;
  p90: number;
  lgbm_point: number | null;
  anomaly_score: number;
  is_holiday: boolean;
  oil_event: boolean;
}

export interface HistoryPoint {
  date: string;
  actual: number;
  predicted: number;
}

export interface AttentionWeight {
  lag_days: number;
  weight: number;
}

export interface EventMarker {
  date: string;
  type: 'holiday' | 'oil_price';
  label: string;
}

export interface ForecastDetail {
  series: SeriesRef;
  horizon: ForecastPoint[];
  history: HistoryPoint[];
  attention: AttentionWeight[];
  events: EventMarker[];
  data_source: string;
}

export interface CatalogResponse {
  stores: number[];
  families: string[];
  products: SeriesRef[];
  series_count: number;
  data_source: string;
}

export interface StockoutAlert {
  product_id: string;
  store_nbr: number;
  family: string;
  p10: number;
  p50: number;
  safe_threshold: number;
  revenue_impact: number;
}

export interface AnomalyFlag {
  product_id: string;
  store_nbr: number;
  family: string;
  forecast_date: string;
  anomaly_score: number;
  p50: number;
}

export interface TopMover {
  product_id: string;
  store_nbr: number;
  family: string;
  p50: number;
  p90: number;
  anomaly_score: number;
}

export interface AccuracySummary {
  mape: number;
  coverage_rate: number;
  coverage_target: number;
  as_of: string;
}

export interface MorningBrief {
  store_health_score: number;
  health_label: 'healthy' | 'watch' | 'at_risk';
  generated_at: string;
  stockout_alerts: StockoutAlert[];
  anomaly_flags: AnomalyFlag[];
  top_movers: TopMover[];
  yesterday_accuracy: AccuracySummary;
  data_source: string;
  cached: boolean;
}

export type ConfidenceMode = 'lean' | 'balanced' | 'safe';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface InventoryRow {
  product_id: string;
  store_nbr: number;
  family: string;
  current_stock: number;
  p10: number;
  p50: number;
  p90: number;
  base_quantity: number;
  safety_buffer: number;
  recommended_qty: number;
  confidence_mode: ConfidenceMode;
  anomaly_score: number;
  risk_level: RiskLevel;
}

export interface InventoryResponse {
  confidence_mode: ConfidenceMode;
  rows: InventoryRow[];
  total_units: number;
  generated_at: string;
  data_source: string;
}

export interface OverridePayload {
  product_id: string;
  store_nbr: number;
  recommended_qty: number;
  override_qty: number;
  reason_code: string;
  note?: string | null;
  confidence_mode: ConfidenceMode;
}

export interface ExportLine {
  product_id: string;
  store_nbr: number;
  family: string;
  order_qty: number;
  unit_cost?: number | null;
}

export interface Scorecard {
  model_name: string;
  current_mape: number;
  previous_mape: number;
  delta_pp: number;
  trend: 'up' | 'down' | 'flat';
  status: 'green' | 'amber' | 'red';
  coverage_rate: number;
  coverage_status: 'green' | 'amber' | 'red';
}

export interface ModelComparisonPoint {
  week_start: string;
  values: Record<string, number>;
}

export interface DriftStatus {
  triggered: boolean;
  mape_delta_pp: number;
  consecutive_weeks: number;
  message: string;
}

export interface PerformanceMonitor {
  coverage_target: number;
  scorecards: Scorecard[];
  comparison: ModelComparisonPoint[];
  models: string[];
  drift: DriftStatus;
  data_source: string;
}

export interface HeatmapCell {
  store_nbr: number;
  family: string;
  coverage_probability: number;
  mape: number;
  series_count: number;
}

export interface CategoryScore {
  family: string;
  mape: number;
  coverage_probability: number;
  rank: number;
}

export interface StoreHealthRow {
  store_nbr: number;
  health_score: number;
  coverage_probability: number;
  mape: number;
  rank: number;
}

export interface AnalyticsGrid {
  stores: number[];
  families: string[];
  cells: HeatmapCell[];
  category_leaderboard: CategoryScore[];
  store_ranking: StoreHealthRow[];
  data_source: string;
}
