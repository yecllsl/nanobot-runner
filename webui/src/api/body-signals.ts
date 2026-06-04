import apiClient from './client';
import type { BodySignalDailyResponse, BodySignalWeeklyResponse, BodySignalAlertsResponse } from '../types/api';

export async function getBodySignalDaily(): Promise<BodySignalDailyResponse> {
  const response = await apiClient.get<BodySignalDailyResponse>('/body-signal/daily');
  return response.data;
}

export async function getBodySignalWeekly(): Promise<BodySignalWeeklyResponse> {
  const response = await apiClient.get<BodySignalWeeklyResponse>('/body-signal/weekly');
  return response.data;
}

export async function getBodySignalAlerts(): Promise<BodySignalAlertsResponse> {
  const response = await apiClient.get<BodySignalAlertsResponse>('/body-signal/alerts');
  return response.data;
}
