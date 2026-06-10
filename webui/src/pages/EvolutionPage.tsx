import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import {
  getEvolutionStatus,
  getTuningParams,
  updateTuningParams,
  listEvolutionReports,
  type EvolutionStatus,
  type TuningParams,
  type ReportMonths,
  type TuningParamsUpdate,
} from '../api/evolution';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function EvolutionPage() {
  const { data: status, loading: statusLoading, execute: fetchStatus } = useApi<EvolutionStatus, []>(getEvolutionStatus);
  const { data: tuning, loading: tuningLoading, execute: fetchTuning } = useApi<TuningParams, []>(getTuningParams);
  const { data: reports, loading: reportsLoading, execute: fetchReports } = useApi<ReportMonths, []>(listEvolutionReports);
  const { execute: doUpdateTuning } = useApi<TuningParams, [TuningParamsUpdate]>(updateTuningParams);
  const [editingTuning, setEditingTuning] = useState<TuningParamsUpdate>({});

  useEffect(() => {
    fetchStatus();
    fetchTuning();
    fetchReports();
  }, [fetchStatus, fetchTuning, fetchReports]);

  const handleTuningChange = (key: keyof TuningParamsUpdate, value: number) => {
    setEditingTuning((prev) => ({ ...prev, [key]: value }));
  };

  const handleTuningSave = async () => {
    if (Object.keys(editingTuning).length > 0) {
      await doUpdateTuning(editingTuning);
      setEditingTuning({});
      fetchTuning();
    }
  };

  const currentTuning = { ...tuning, ...editingTuning };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">进化控制台</h1>

      {(statusLoading || tuningLoading || reportsLoading) && <LoadingSpinner />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 引擎状态 */}
        {status && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">引擎状态</h2>
              <span className="flex items-center gap-1.5 text-sm text-green-600">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                运行中
              </span>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-500">触发条件</h3>
              {status.trigger_conditions.map((tc) => (
                <div key={tc.rule} className="flex items-center justify-between py-1">
                  <span className="text-sm text-gray-700">{tc.description}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    tc.is_triggered ? 'bg-amber-50 text-amber-700' : 'bg-gray-50 text-gray-400'
                  }`}>
                    {tc.is_triggered ? '已触发' : '未触发'}
                  </span>
                </div>
              ))}
            </div>

            {status.recent_actions.length > 0 && (
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-medium text-gray-500">最近动作</h3>
                {status.recent_actions.map((action, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{action.action_type}</span>
                    <span className={`text-xs ${action.status === 'completed' ? 'text-green-600' : 'text-amber-600'}`}>
                      {action.status === 'completed' ? '已完成' : '待执行'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 提示参数调优 */}
        {currentTuning && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">提示参数调优</h2>
              <button
                onClick={handleTuningSave}
                disabled={Object.keys(editingTuning).length === 0}
                className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                保存
              </button>
            </div>

            <div className="space-y-4">
              {([
                { key: 'tone' as const, label: '语气强度', desc: '控制AI回复的语气倾向' },
                { key: 'detail' as const, label: '详细程度', desc: '控制AI回复的详细程度' },
                { key: 'aggressive' as const, label: '推荐激进性', desc: '控制训练推荐的激进程度' },
                { key: 'data_driven' as const, label: '数据驱动权重', desc: '控制数据驱动vs经验驱动的权重' },
              ]).map(({ key, label, desc }) => (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{label}</span>
                    <span className="text-sm text-gray-500">{(currentTuning[key] ?? 0.5).toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={currentTuning[key] ?? 0.5}
                    onChange={(e) => handleTuningChange(key, parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
                  />
                  <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 进化报告 */}
      {reports && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">进化报告</h2>
          {reports.available_months.length === 0 ? (
            <p className="text-gray-400 text-sm">暂无可用报告</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {reports.available_months.map((month) => (
                <Link
                  key={month}
                  to={`/evolution/reports/${month}`}
                  className="block text-center py-3 px-2 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <span className="text-sm font-medium text-gray-700">{month}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
