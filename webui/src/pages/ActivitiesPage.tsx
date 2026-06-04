import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getActivities } from '../api/activities';
import { formatPace, formatDuration, formatDistance, formatDateString } from '../utils/format';
import LoadingSpinner from '../components/common/LoadingSpinner';
import type { ActivitiesResponse } from '../types/api';

export default function ActivitiesPage() {
  const [limit] = useState(20);
  const { data, loading, execute } = useApi<ActivitiesResponse, [number]>(getActivities);

  useEffect(() => {
    execute(limit);
  }, [limit, execute]);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">活动记录</h2>

      {loading && <LoadingSpinner />}

      {data && (
        <>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">日期</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">距离</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">时长</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">配速</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">心率</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((activity, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className="text-primary-600 font-medium">{formatDateString(activity.timestamp)}</span>
                    </td>
                    <td className="text-right px-4 py-3 text-gray-700">{formatDistance(activity.distance_m)}</td>
                    <td className="text-right px-4 py-3 text-gray-700">{formatDuration(activity.duration_s)}</td>
                    <td className="text-right px-4 py-3 text-gray-700">{formatPace(activity.avg_pace_sec_km)}</td>
                    <td className="text-right px-4 py-3 text-gray-700">{activity.avg_heart_rate ? `${activity.avg_heart_rate} bpm` : '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.count === 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">暂无活动记录</div>
          )}
        </>
      )}
    </div>
  );
}
