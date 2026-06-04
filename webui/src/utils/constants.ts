/** 时间范围选项 */
export const TIME_RANGE_OPTIONS = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '90天', value: 90 },
  { label: '365天', value: 365 },
] as const;

/** 各页面默认时间范围（天） */
export const DEFAULT_TIME_RANGES: Record<string, number> = {
  dashboard: 7,
  vdot: 30,
  trainingLoad: 42,
  bodySignals: 7,
};

/** 疲劳状态 */
export const FITNESS_STATUS = {
  FRESH: '新鲜',
  OPTIMAL: '最佳',
  FATIGUED: '疲劳',
  OVER_TRAINED: '过度训练',
} as const;

/** TSB疲劳状态判定 */
export function getFitnessStatus(tsb: number): string {
  if (tsb > 15) return FITNESS_STATUS.FRESH;
  if (tsb > 0) return FITNESS_STATUS.OPTIMAL;
  if (tsb > -30) return FITNESS_STATUS.FATIGUED;
  return FITNESS_STATUS.OVER_TRAINED;
}

/** TSB疲劳状态对应颜色 */
export function getFitnessStatusColor(status: string): string {
  switch (status) {
    case FITNESS_STATUS.FRESH: return 'text-green-600';
    case FITNESS_STATUS.OPTIMAL: return 'text-blue-600';
    case FITNESS_STATUS.FATIGUED: return 'text-yellow-600';
    case FITNESS_STATUS.OVER_TRAINED: return 'text-red-600';
    default: return 'text-gray-600';
  }
}

/** TSB疲劳状态对应背景色 */
export function getFitnessStatusBg(status: string): string {
  switch (status) {
    case FITNESS_STATUS.FRESH: return 'bg-green-50 border-green-200';
    case FITNESS_STATUS.OPTIMAL: return 'bg-blue-50 border-blue-200';
    case FITNESS_STATUS.FATIGUED: return 'bg-yellow-50 border-yellow-200';
    case FITNESS_STATUS.OVER_TRAINED: return 'bg-red-50 border-red-200';
    default: return 'bg-gray-50 border-gray-200';
  }
}

/** Agent对话链接 */
export const AGENT_CHAT_URL = 'http://127.0.0.1:8765';
