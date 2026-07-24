import apiClient from './client';

export interface ImportResult {
  filename: string;
  status: 'added' | 'skipped' | 'error';
  message: string;
}

export interface ImportResponse {
  results: ImportResult[];
  summary: { total: number; added: number; skipped: number; errors: number };
}

/**
 * 上传 FIT 文件并触发导入
 * SUG-03: 不手动设置 Content-Type，axios 发送 FormData 时会自动设置含 boundary 的正确 header
 */
export async function importData(
  files: File[],
  force: boolean = false,
): Promise<ImportResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const response = await apiClient.post<ImportResponse>('/data/import', formData, {
    params: { force },
    timeout: 300000, // 5 分钟，大批量导入需要更长时间
  });
  return response.data;
}
