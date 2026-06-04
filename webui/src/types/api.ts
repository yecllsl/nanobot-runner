// ===== 通用 =====
export interface HealthResponse {
  status: string;
  version: string;
}

// ===== Dashboard =====
export interface DashboardResponse {
  training_load: TrainingLoadData;
  body_signal: BodySignalSummary;
}

export interface TrainingLoadData {
  atl: number;
  ctl: number;
  tsb: number;
  fitness_status: string;
  training_advice: string;
  days_analyzed: number;
  runs_count: number;
}

export interface BodySignalSummary {
  recovery_status: string;
  fatigue_score: number;
  data_quality: string;
  daily_summary: string;
  training_advice: string;
  alerts: BodySignalAlert[];
}

export interface BodySignalAlert {
  alert_type: string;
  severity: string;
  message: string;
}

// ===== VDOT =====
export interface VdotTrendItem {
  date: string;
  vdot: number;
  distance: number;
  duration: number;
}

export interface VdotTrendResponse {
  items: VdotTrendItem[];
  days: number;
  count: number;
}

// ===== 训练负荷 =====
export interface TrainingLoadResponse {
  atl: number;
  ctl: number;
  tsb: number;
  fitness_status: string;
  training_advice: string;
  days_analyzed: number;
  runs_count: number;
}

export interface TrainingLoadTrendItem {
  date: string;
  tss: number;
  atl: number;
  ctl: number;
  tsb: number;
}

export interface TrainingLoadTrendResponse {
  trend_data: TrainingLoadTrendItem[];
  summary: {
    current_atl: number;
    current_ctl: number;
    current_tsb: number;
    status: string;
    recommendation: string;
  };
  days_analyzed: number;
  total_runs: number;
}

// ===== 活动 =====
export interface SessionDetail {
  timestamp: string;
  distance_km: number;
  duration_min: number;
  avg_pace_sec_km: number;
  avg_heart_rate: number | null;
  distance_m: number;
  duration_s: number;
  max_heart_rate: number | null;
  calories: number | null;
}

export interface ActivitiesResponse {
  items: SessionDetail[];
  count: number;
  limit: number;
}

// ===== 身体信号 =====
export interface BodySignalDailyResponse {
  recovery_status: string;
  fatigue_score: number;
  data_quality: string;
  daily_summary: string;
  training_advice: string;
  alerts: BodySignalAlert[];
}

export interface BodySignalWeeklyResponse {
  recovery_status: string;
  fatigue_score: number;
  data_quality: string;
  daily_summary: string;
  training_advice: string;
  alerts: BodySignalAlert[];
}

export interface BodySignalAlertsResponse {
  alerts: BodySignalAlert[];
  count: number;
}
