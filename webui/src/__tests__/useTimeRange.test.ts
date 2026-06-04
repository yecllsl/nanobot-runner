import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTimeRange } from '../hooks/useTimeRange';

describe('useTimeRange', () => {
  it('默认值为传入的初始值', () => {
    const { result } = renderHook(() => useTimeRange(90));
    expect(result.current.days).toBe(90);
  });

  it('setDays 更新天数', () => {
    const { result } = renderHook(() => useTimeRange(90));
    act(() => {
      result.current.setDays(30);
    });
    expect(result.current.days).toBe(30);
  });
});
