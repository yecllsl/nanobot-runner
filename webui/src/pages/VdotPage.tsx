import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getVdotTrend } from '../api/vdot';
import { DEFAULT_TIME_RANGES } from '../utils/constants';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import VdotTrendChart from '../components/charts/VdotTrendChart';
import type { VdotTrendResponse } from '../types/api';

export default function VdotPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.vdot);
  const { data, loading, execute } = useApi<VdotTrendResponse, [number]>(getVdotTrend);

  useEffect(() => {
    execute(days);
  }, [days, execute]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">VDOT 趋势</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {data && (
        <>
          <VdotTrendChart data={data.items} />
          {data.items.length > 0 && (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-sm text-gray-500">最新VDOT</p>
                <p className="text-2xl font-bold text-primary-600">{data.items[data.items.length - 1].vdot.toFixed(1)}</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-sm text-gray-500">最高VDOT</p>
                <p className="text-2xl font-bold text-green-600">{Math.max(...data.items.map((i) => i.vdot)).toFixed(1)}</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className="text-sm text-gray-500">数据点</p>
                <p className="text-2xl font-bold text-gray-900">{data.items.length}</p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
