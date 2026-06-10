import apiClient from './client';

/** 训练计划列表项 */
export interface PlanListItem {
  plan_id: string;
  goal: string;
  start_date: string;
  end_date: string;
  status: string;
  total_weeks: number;
}

/** 日历日项 */
export interface CalendarDay {
  date: string;
  has_plan: boolean;
  plan_id?: string;
  workout_type?: string;
  completed?: boolean;
}

/** 计划详情 */
export interface PlanDetail {
  plan_id: string;
  goal: string;
  start_date: string;
  end_date: string;
  status: string;
  weeks: PlanWeek[];
}

/** 计划周 */
export interface PlanWeek {
  week_number: number;
  phase: string;
  daily_plans: DailyPlan[];
}

/** 单日计划 */
export interface DailyPlan {
  date: string;
  workout_type: string;
  distance_km: number;
  duration_min: number;
  intensity: string;
  description: string;
  completed: boolean;
}

/** 计划进度 */
export interface PlanProgress {
  plan_id: string;
  total_days: number;
  completed_days: number;
  completion_rate: number;
  weekly_progress: WeeklyProgress[];
}

/** 周进度 */
export interface WeeklyProgress {
  week_number: number;
  completed_days: number;
  total_days: number;
}

/** 单日计划更新请求 */
export interface DailyPlanUpdate {
  workout_type?: string;
  distance_km?: number;
  duration_min?: number;
  intensity?: string;
  description?: string;
  completed?: boolean;
}

/** 获取训练计划列表 */
export async function listPlans(status?: string, limit: number = 100): Promise<{ plans: PlanListItem[] }> {
  const params: Record<string, string | number> = { limit };
  if (status) params.status = status;
  const response = await apiClient.get('/plan/list', { params });
  return response.data;
}

/** 获取日历视图 */
export async function getPlanCalendar(
  year: number,
  month: number,
  view: 'month' | 'week' = 'month',
): Promise<{ days: CalendarDay[] }> {
  const response = await apiClient.get('/plan/calendar', { params: { year, month, view } });
  return response.data;
}

/** 获取计划详情 */
export async function getPlanDetail(planId: string): Promise<PlanDetail> {
  const response = await apiClient.get(`/plan/${planId}`);
  return response.data;
}

/** 获取计划进度 */
export async function getPlanProgress(planId: string): Promise<PlanProgress> {
  const response = await apiClient.get(`/plan/progress/${planId}`);
  return response.data;
}

/** 更新单日训练详情 */
export async function updateDailyPlan(
  planId: string,
  date: string,
  update: DailyPlanUpdate,
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.put(`/plan/daily/${planId}/${date}`, update);
  return response.data;
}
