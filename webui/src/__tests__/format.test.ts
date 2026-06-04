import { describe, it, expect } from 'vitest';
import { formatPace, formatPaceWithUnit, formatDuration, formatDistance, formatVdot } from '../utils/format';

describe('formatPace', () => {
  it('格式化配速（不含单位）', () => {
    expect(formatPace(330)).toBe('5\'30"');
  });
  it('整分配速', () => {
    expect(formatPace(300)).toBe('5\'00"');
  });
});

describe('formatPaceWithUnit', () => {
  it('格式化配速（含单位）', () => {
    expect(formatPaceWithUnit(330)).toBe('5\'30"/km');
  });
  it('整分配速（含单位）', () => {
    expect(formatPaceWithUnit(300)).toBe('5\'00"/km');
  });
});

describe('formatDuration', () => {
  it('格式化时长', () => {
    expect(formatDuration(5025)).toBe('01:23:45');
  });
  it('不足1小时', () => {
    expect(formatDuration(1865)).toBe('00:31:05');
  });
});

describe('formatDistance', () => {
  it('格式化距离', () => {
    expect(formatDistance(10234)).toBe('10.23 km');
  });
});

describe('formatVdot', () => {
  it('格式化VDOT', () => {
    expect(formatVdot(45.23)).toBe('45.2');
  });
});
