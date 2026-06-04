import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getActivityDetail } from '../api/activities';
import { formatPace, formatDuration, formatDistance, formatHeartRate, formatDateString } from '../utils/format';
import StatCard from '../components/cards/StatCard';
import LoadingSpinner from '../components/common/LoadingSpinner';
import type { SessionDetail } from '../types/api';

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, loading, execute } = useApi<SessionDetail, [string]>(getActivityDetail);

  useEffect(() => {
    if (id) {
      execute(id);
    }
  }, [id, execute]);

  if (loading) return <LoadingSpinner />;

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">未找到活动数据</p>
        <Link to="/activities" className="text-primary-600 hover:underline mt-2 inline-block">返回活动列表</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/activities" className="text-primary-600 hover:underline text-sm">← 返回列表</Link>
        <h2 className="text-xl font-bold text-gray-900">{formatDateString(data.timestamp)}</h2>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard title="距离" value={formatDistance(data.distance_m)} />
        <StatCard title="时长" value={formatDuration(data.duration_s)} />
        <StatCard title="配速" value={formatPace(data.avg_pace_sec_km)} />
        <StatCard title="心率" value={data.avg_heart_rate ? formatHeartRate(data.avg_heart_rate) : '--'} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <StatCard title="最大心率" value={data.max_heart_rate ? formatHeartRate(data.max_heart_rate) : '--'} />
        <StatCard title="卡路里" value={data.calories ? `${data.calories} kcal` : '--'} />
        <StatCard title="距离(km)" value={`${data.distance_km} km`} />
      </div>
    </div>
  );
}
