/**
 * 格式化配速为 M'SS"/km
 */
export function formatPace(secondsPerKm: number): string {
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.floor(secondsPerKm % 60);
  return `${minutes}'${seconds.toString().padStart(2, '0')}"`;
}

/**
 * 格式化配速为 M'SS"/km（含单位）
 */
export function formatPaceWithUnit(secondsPerKm: number): string {
  return `${formatPace(secondsPerKm)}/km`;
}

/**
 * 格式化时长为 HH:MM:SS
 */
export function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * 格式化距离为 km（保留2位小数）
 */
export function formatDistance(meters: number): string {
  const km = meters / 1000;
  return `${km.toFixed(2)} km`;
}

/**
 * 格式化心率为 bpm
 */
export function formatHeartRate(hr: number): string {
  return `${hr} bpm`;
}

/**
 * 格式化VDOT（保留1位小数）
 */
export function formatVdot(vdot: number): string {
  return vdot.toFixed(1);
}

/**
 * 格式化日期字符串
 */
export function formatDateString(dateStr: string): string {
  return dateStr.split('T')[0];
}
