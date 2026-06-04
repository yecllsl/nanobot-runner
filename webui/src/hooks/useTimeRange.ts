import { useState, useCallback } from 'react';

export function useTimeRange(defaultDays: number) {
  const [days, setDays] = useState(defaultDays);

  const handleDaysChange = useCallback((newDays: number) => {
    setDays(newDays);
  }, []);

  return { days, setDays: handleDaysChange };
}
