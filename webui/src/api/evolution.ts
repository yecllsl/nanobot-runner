import apiClient from './client';

/** 触发条件 */
export interface TriggerCondition {
  rule: string;
  description: string;
  is_triggered: boolean;
}

/** 最近动作 */
export interface RecentAction {
  action_type: string;
  triggered_at: string;
  status: string;
}

/** 进化引擎状态 */
export interface EvolutionStatus {
  engine_status: string;
  trigger_conditions: TriggerCondition[];
  recent_actions: RecentAction[];
}

/** 提示调优参数 */
export interface TuningParams {
  tone: number;
  detail: number;
  aggressive: number;
  data_driven: number;
}

/** 提示调优参数更新请求 */
export interface TuningParamsUpdate {
  tone?: number;
  detail?: number;
  aggressive?: number;
  data_driven?: number;
}

/** 报告月份列表 */
export interface ReportMonths {
  available_months: string[];
  count: number;
}

/** 进化报告详情 */
export interface EvolutionReport {
  report_id: string;
  month: string;
  total_decisions: number;
  [key: string]: unknown;
}

/** 获取进化引擎状态（只读，不触发任何进化动作） */
export async function getEvolutionStatus(): Promise<EvolutionStatus> {
  const response = await apiClient.get('/evolution/status');
  return response.data;
}

/** 获取当前提示调优参数 */
export async function getTuningParams(): Promise<TuningParams> {
  const response = await apiClient.get('/evolution/tuning');
  return response.data;
}

/** 更新提示调优参数 */
export async function updateTuningParams(params: TuningParamsUpdate): Promise<TuningParams> {
  const response = await apiClient.put('/evolution/tuning', params);
  return response.data;
}

/** 获取可用的进化报告月份列表 */
export async function listEvolutionReports(): Promise<ReportMonths> {
  const response = await apiClient.get('/evolution/reports');
  return response.data;
}

/** 获取指定月份进化报告 */
export async function getEvolutionReport(month: string): Promise<EvolutionReport> {
  const response = await apiClient.get(`/evolution/reports/${month}`);
  return response.data;
}
