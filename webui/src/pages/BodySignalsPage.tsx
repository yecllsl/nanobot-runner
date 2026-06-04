import { useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { useTimeRange } from '../hooks/useTimeRange';
import { getBodySignalDaily, getBodySignalWeekly, getBodySignalAlerts } from '../api/body-signals';
import { DEFAULT_TIME_RANGES } from '../utils/constants';
import LoadingSpinner from '../components/common/LoadingSpinner';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import StatusCard from '../components/cards/StatusCard';
import AlertCard from '../components/cards/AlertCard';
import type { BodySignalDailyResponse, BodySignalWeeklyResponse, BodySignalAlertsResponse } from '../types/api';

export default function BodySignalsPage() {
  const { days, setDays } = useTimeRange(DEFAULT_TIME_RANGES.bodySignals);
  const { data: dailyData, loading: dailyLoading, execute: executeDaily } = useApi<BodySignalDailyResponse, []>(getBodySignalDaily);
  const { data: weeklyData, loading: weeklyLoading, execute: executeWeekly } = useApi<BodySignalWeeklyResponse, []>(getBodySignalWeekly);
  const { data: alertsData, loading: alertsLoading, execute: executeAlerts } = useApi<BodySignalAlertsResponse, []>(getBodySignalAlerts);

  useEffect(() => {
    executeDaily();
    executeWeekly();
    executeAlerts();
  }, [days, executeDaily, executeWeekly, executeAlerts]);

  const loading = dailyLoading || weeklyLoading || alertsLoading;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">身体信号</h2>
        <TimeRangeSelector value={days} onChange={setDays} />
      </div>

      {loading && <LoadingSpinner />}

      {/* 每日摘要 */}
      {dailyData && (
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-3">今日状态</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatusCard title="恢复状态" status={dailyData.recovery_status} description="当前恢复水平" />
            <StatusCard title="疲劳度" status={dailyData.fatigue_score.toFixed(0)} description="0-100分" />
            <StatusCard title="数据质量" status={dailyData.data_quality} description="数据充分性" />
            <StatusCard title="训练建议" status={dailyData.training_advice} description="基于身体状态" />
          </div>
        </section>
      )}

      {/* 本周摘要 */}
      {weeklyData && (
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-3">本周状态</h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            <StatusCard title="恢复状态" status={weeklyData.recovery_status} description="本周恢复水平" />
            <StatusCard title="疲劳度" status={weeklyData.fatigue_score.toFixed(0)} description="0-100分" />
            <StatusCard title="训练建议" status={weeklyData.training_advice} description="基于本周状态" />
          </div>
        </section>
      )}

      {/* 预警 */}
      {alertsData && alertsData.alerts.length > 0 && (
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-3">预警</h3>
          <div className="space-y-3">
            {alertsData.alerts.map((alert, idx) => (
              <AlertCard
                key={idx}
                level={alert.severity === 'warning' ? 'warning' : alert.severity === 'danger' ? 'danger' : 'info'}
                title={alert.alert_type}
                message={alert.message}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
