import apiClient from './client';

/** 个人信息 */
export interface Profile {
  nickname: string;
  age: number;
  gender: string;
  max_heart_rate: number;
  resting_heart_rate: number;
}

/** 个人信息更新请求 */
export interface ProfileUpdate {
  nickname?: string;
  age?: number;
  gender?: string;
  max_heart_rate?: number;
  resting_heart_rate?: number;
}

/** 系统配置 */
export interface SystemConfig {
  data_dir: string;
  version: string;
  webui_enabled: boolean;
  webui_port: number;
  gateway_status: string;
}

/** 获取个人信息配置 */
export async function getProfile(): Promise<Profile> {
  const response = await apiClient.get('/settings/profile');
  return response.data;
}

/** 更新个人信息配置 */
export async function updateProfile(update: ProfileUpdate): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.put('/settings/profile', update);
  return response.data;
}

/** 获取系统配置（只读） */
export async function getSystemConfig(): Promise<SystemConfig> {
  const response = await apiClient.get('/settings/system');
  return response.data;
}
