import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { listPlans, getPlanDetail, getPlanProgress, type PlanListItem, type PlanDetail, type PlanProgress, type DailyPlan } from '../api/plan';
import DailyPlanEditor from '../components/plan/DailyPlanEditor';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function PlanPage() {
  const { data: plansData, loading: plansLoading, execute: fetchPlans } = useApi<{ plans: PlanListItem[] }, [string | undefined]>(listPlans);
  const { data: planDetail, loading: detailLoading, execute: fetchDetail } = useApi<PlanDetail, [string]>(getPlanDetail);
  const { data: planProgress, execute: fetchProgress } = useApi<PlanProgress, [string]>(getPlanProgress);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [editingDay, setEditingDay] = useState<DailyPlan | null>(null);

  useEffect(() => {
    fetchPlans(statusFilter);
  }, [statusFilter, fetchPlans]);

  useEffect(() => {
    if (selectedPlanId) {
      fetchDetail(selectedPlanId);
      fetchProgress(selectedPlanId);
    }
  }, [selectedPlanId, fetchDetail, fetchProgress]);

  const plans = plansData?.plans ?? [];

  const handleRefreshDetail = () => {
    if (selectedPlanId) {
      fetchDetail(selectedPlanId);
      fetchProgress(selectedPlanId);
    }
  };

  const handleAiAdjust = () => {
    if (selectedPlanId) {
      window.open(`http://127.0.0.1:8765?plan_id=${selectedPlanId}`, '_blank');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">训练计划</h1>
        <div className="flex gap-2">
          {['active', 'completed', 'all'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s === 'all' ? undefined : s)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                (s === 'all' ? !statusFilter : statusFilter === s)
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              {s === 'all' ? '全部' : s === 'active' ? '进行中' : '已完成'}
            </button>
          ))}
        </div>
      </div>

      {plansLoading && <LoadingSpinner />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 计划列表 */}
        <div className="lg:col-span-1 space-y-3">
          {plans.length === 0 && !plansLoading && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              暂无训练计划
            </div>
          )}
          {plans.map((plan) => (
            <button
              key={plan.plan_id}
              onClick={() => setSelectedPlanId(plan.plan_id)}
              className={`w-full text-left bg-white rounded-xl border p-4 transition-colors ${
                selectedPlanId === plan.plan_id
                  ? 'border-primary-300 ring-1 ring-primary-200'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900 truncate">{plan.goal}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  plan.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {plan.status === 'active' ? '进行中' : plan.status}
                </span>
              </div>
              <div className="text-sm text-gray-500">
                {plan.start_date} ~ {plan.end_date} | {plan.total_weeks}周
              </div>
            </button>
          ))}
        </div>

        {/* 计划详情 */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedPlanId && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              请从左侧选择一个计划查看详情
            </div>
          )}

          {detailLoading && <LoadingSpinner />}

          {planDetail && (
            <>
              {/* 进度概览 + AI调整按钮 */}
              {planProgress && (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-500">执行进度</h3>
                    <button
                      onClick={handleAiAdjust}
                      className="px-3 py-1 text-xs font-medium text-primary-700 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
                    >
                      AI调整
                    </button>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="w-full bg-gray-100 rounded-full h-3">
                        <div
                          className="bg-primary-500 h-3 rounded-full transition-all"
                          style={{ width: `${Math.min(planProgress.completion_rate * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-lg font-bold text-primary-600">
                      {(planProgress.completion_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex gap-4 mt-2 text-sm text-gray-500">
                    <span>总天数: {planProgress.total_days}</span>
                    <span>已完成: {planProgress.completed_days}</span>
                  </div>
                </div>
              )}

              {/* 周列表 */}
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-500 mb-3">训练周</h3>
                <div className="space-y-3">
                  {planDetail.weeks.map((week) => (
                    <div key={week.week_number} className="border border-gray-100 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-800">第{week.week_number}周</span>
                        <span className="text-xs text-gray-400">{week.phase}</span>
                      </div>
                      <div className="grid grid-cols-7 gap-1">
                        {week.daily_plans.map((day) => (
                          <button
                            key={day.date}
                            onClick={() => setEditingDay(day)}
                            className={`text-center text-xs p-1 rounded cursor-pointer transition-colors hover:ring-2 hover:ring-primary-300 ${
                              day.completed
                                ? 'bg-green-50 text-green-700'
                                : 'bg-gray-50 text-gray-500'
                            }`}
                            title={`${day.date} ${day.workout_type} ${day.distance_km}km - 点击编辑`}
                          >
                            <div>{day.date.slice(-2)}</div>
                            <div className="truncate">{day.workout_type?.slice(0, 2) || '-'}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 日计划编辑弹窗 */}
      {editingDay && selectedPlanId && (
        <DailyPlanEditor
          planId={selectedPlanId}
          day={editingDay}
          onClose={() => setEditingDay(null)}
          onSaved={handleRefreshDetail}
        />
      )}
    </div>
  );
}
