import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getDashboard } from '../api/dashboard';
import { DEFAULT_TIME_RANGES } from '../utils/constants';
import StatCard from '../components/cards/StatCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import type { DashboardResponse } from '../types/api';

export default function DashboardPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.dashboard);
  const { data, loading, execute } = useApi<DashboardResponse, [number]>(getDashboard);

  useEffect(() => {
    execute(days);
  }, [days, execute]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">今日概览</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {data && (
        <>
          {/* 训练负荷 */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-3">训练负荷</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <StatCard title="ATL (急性)" value={data.training_load.atl.toFixed(1)} subtitle="7天训练负荷" />
              <StatCard title="CTL (慢性)" value={data.training_load.ctl.toFixed(1)} subtitle="42天体能基础" />
              <StatCard title="TSB (平衡)" value={data.training_load.tsb.toFixed(1)} subtitle="CTL - ATL" />
              <StatCard title="状态" value={data.training_load.fitness_status} />
            </div>
          </section>

          {/* 身体信号 */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-3">身体信号</h3>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              <StatCard title="恢复状态" value={data.body_signal.recovery_status} />
              <StatCard title="疲劳度" value={data.body_signal.fatigue_score.toFixed(0)} subtitle="0-100" />
              <StatCard title="训练建议" value={data.body_signal.training_advice} />
            </div>
          </section>

          {/* 快捷入口 */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-3">快捷入口</h3>
            <div className="grid grid-cols-3 gap-3">
              <a href="/vdot" className="bg-white rounded-xl border border-gray-200 p-4 text-center hover:border-primary-300 transition-colors">
                <p className="text-2xl">📈</p>
                <p className="text-sm font-medium text-gray-700 mt-1">VDOT趋势</p>
              </a>
              <a href="/training-load" className="bg-white rounded-xl border border-gray-200 p-4 text-center hover:border-primary-300 transition-colors">
                <p className="text-2xl">💪</p>
                <p className="text-sm font-medium text-gray-700 mt-1">训练负荷</p>
              </a>
              <a href="/activities" className="bg-white rounded-xl border border-gray-200 p-4 text-center hover:border-primary-300 transition-colors">
                <p className="text-2xl">🏃</p>
                <p className="text-sm font-medium text-gray-700 mt-1">活动记录</p>
              </a>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
