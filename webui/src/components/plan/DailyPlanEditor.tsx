import { useState } from 'react';
import { updateDailyPlan, type DailyPlan } from '../../api/plan';

interface DailyPlanEditorProps {
  planId: string;
  day: DailyPlan;
  onClose: () => void;
  onSaved: () => void;
}

export default function DailyPlanEditor({ planId, day, onClose, onSaved }: DailyPlanEditorProps) {
  const [completed, setCompleted] = useState(day.completed);
  const [effortScore, setEffortScore] = useState(5);
  const [notes, setNotes] = useState(day.description ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await updateDailyPlan(planId, day.date, {
        completed,
        description: notes,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题 */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">编辑训练日</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        {/* 基本信息（只读） */}
        <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">日期</span>
            <span className="font-medium text-gray-900">{day.date}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">类型</span>
            <span className="font-medium text-gray-900">{day.workout_type}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">距离</span>
            <span className="font-medium text-gray-900">{day.distance_km} km</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">时长</span>
            <span className="font-medium text-gray-900">{day.duration_min} min</span>
          </div>
        </div>

        {/* 完成状态 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">完成状态</label>
          <div className="flex gap-3">
            <button
              onClick={() => setCompleted(true)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                completed ? 'bg-green-50 text-green-700 border-2 border-green-300' : 'bg-gray-50 text-gray-500 border border-gray-200'
              }`}
            >
              已完成
            </button>
            <button
              onClick={() => setCompleted(false)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                !completed ? 'bg-amber-50 text-amber-700 border-2 border-amber-300' : 'bg-gray-50 text-gray-500 border border-gray-200'
              }`}
            >
              未完成
            </button>
          </div>
        </div>

        {/* 体感评分 */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">体感评分</label>
            <span className="text-sm text-gray-500">{effortScore}/10</span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            step="1"
            value={effortScore}
            onChange={(e) => setEffortScore(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-0.5">
            <span>轻松</span>
            <span>极限</span>
          </div>
        </div>

        {/* 备注 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="记录训练感受、身体状况..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
          />
        </div>

        {/* 错误提示 */}
        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
