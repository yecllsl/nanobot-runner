import apiClient from './client';
import type { VdotTrendResponse } from '../types/api';

export async function getVdotTrend(days: number = 30): Promise<VdotTrendResponse> {
  const response = await apiClient.get<VdotTrendResponse>('/vdot/trend', { params: { days } });
  return response.data;
}
