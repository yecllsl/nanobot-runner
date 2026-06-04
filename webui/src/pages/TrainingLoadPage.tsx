import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getTrainingLoad, getTrainingLoadTrend } from '../api/training-load';
import { DEFAULT_TIME_RANGES, getFitnessStatusColor, getFitnessStatusBg } from '../utils/constants';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import TrainingLoadChart from '../components/charts/TrainingLoadChart';
import StatusCard from '../components/cards/StatusCard';
import AlertCard from '../components/cards/AlertCard';
import type { TrainingLoadResponse, TrainingLoadTrendResponse } from '../types/api';

export default function TrainingLoadPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.trainingLoad);
  const { data: loadData, loading: loadLoading, execute: executeLoad } = useApi<TrainingLoadResponse, [number]>(getTrainingLoad);
  const { data: trendData, loading: trendLoading, execute: executeTrend } = useApi<TrainingLoadTrendResponse, [number]>(getTrainingLoadTrend);

  useEffect(() => {
    executeLoad(days);
    executeTrend(days);
  }, [days, executeLoad, executeTrend]);

  const loading = loadLoading || trendLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">训练负荷</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {loadData && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className={`rounded-xl border p-4 ${getFitnessStatusBg(loadData.fitness_status)}`}>
              <p className="text-sm text-gray-500 font-medium">疲劳状态</p>
              <p className={`mt-1 text-xl font-bold ${getFitnessStatusColor(loadData.fitness_status)}`}>{loadData.fitness_status}</p>
            </div>
            <StatusCard title="ATL (急性)" status={loadData.atl.toFixed(1)} description="7天训练负荷" />
            <StatusCard title="CTL (慢性)" status={loadData.ctl.toFixed(1)} description="42天体能基础" />
            <StatusCard title="TSB (平衡)" status={loadData.tsb.toFixed(1)} description="CTL - ATL" />
          </div>

          {loadData.tsb < -30 && (
            <AlertCard level="danger" title="过度训练预警"
              message={`TSB = ${loadData.tsb.toFixed(1)}，训练负荷过高，建议减少训练量`} />
          )}
        </>
      )}

      {trendData && <TrainingLoadChart data={trendData.trend_data} />}
    </div>
  );
}
