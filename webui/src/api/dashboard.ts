import apiClient from './client';
import type { DashboardResponse } from '../types/api';

export async function getDashboard(days: number = 7): Promise<DashboardResponse> {
  const response = await apiClient.get<DashboardResponse>('/dashboard', { params: { days } });
  return response.data;
}
