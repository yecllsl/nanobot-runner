import apiClient from './client';
import type { ActivitiesResponse, SessionDetail } from '../types/api';

export async function getActivities(limit: number = 20): Promise<ActivitiesResponse> {
  const response = await apiClient.get<ActivitiesResponse>('/activities', { params: { limit } });
  return response.data;
}

export async function getActivityDetail(id: string): Promise<SessionDetail> {
  const response = await apiClient.get<SessionDetail>(`/activities/${id}`);
  return response.data;
}
