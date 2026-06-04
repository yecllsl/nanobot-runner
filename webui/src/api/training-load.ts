import apiClient from './client';
import type { TrainingLoadResponse, TrainingLoadTrendResponse } from '../types/api';

export async function getTrainingLoad(days: number = 42): Promise<TrainingLoadResponse> {
  const response = await apiClient.get<TrainingLoadResponse>('/training-load', { params: { days } });
  return response.data;
}

export async function getTrainingLoadTrend(days: number = 90): Promise<TrainingLoadTrendResponse> {
  const response = await apiClient.get<TrainingLoadTrendResponse>('/training-load/trend', { params: { days } });
  return response.data;
}
