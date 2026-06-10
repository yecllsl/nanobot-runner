import { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { getProfile, updateProfile, getSystemConfig, type Profile, type ProfileUpdate, type SystemConfig } from '../api/settings';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function SettingsPage() {
  const { data: profile, loading: profileLoading, execute: fetchProfile } = useApi<Profile, []>(getProfile);
  const { data: system, loading: systemLoading, execute: fetchSystem } = useApi<SystemConfig, []>(getSystemConfig);
  const { execute: doUpdateProfile } = useApi<{ success: boolean; message: string }, [ProfileUpdate]>(updateProfile);
  const [editForm, setEditForm] = useState<ProfileUpdate>({});
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchSystem();
  }, [fetchProfile, fetchSystem]);

  const handleSave = async () => {
    if (Object.keys(editForm).length > 0) {
      const result = await doUpdateProfile(editForm);
      if (result) {
        setSaveSuccess(true);
        setEditForm({});
        setTimeout(() => setSaveSuccess(false), 2000);
        fetchProfile();
      }
    }
  };

  const currentProfile = { ...profile, ...editForm };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">设置中心</h1>

      {(profileLoading || systemLoading) && <LoadingSpinner />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 个人信息 */}
        {currentProfile && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">个人信息</h2>
              <button
                onClick={handleSave}
                disabled={Object.keys(editForm).length === 0}
                className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {saveSuccess ? '已保存' : '保存'}
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">昵称</label>
                <input
                  type="text"
                  value={currentProfile.nickname ?? ''}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, nickname: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">年龄</label>
                  <input
                    type="number"
                    value={currentProfile.age ?? 0}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, age: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">性别</label>
                  <select
                    value={currentProfile.gender ?? ''}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, gender: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">未设置</option>
                    <option value="male">男</option>
                    <option value="female">女</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">最大心率</label>
                  <input
                    type="number"
                    value={currentProfile.max_heart_rate ?? 190}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, max_heart_rate: parseInt(e.target.value) || 190 }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">静息心率</label>
                  <input
                    type="number"
                    value={currentProfile.resting_heart_rate ?? 60}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, resting_heart_rate: parseInt(e.target.value) || 60 }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 系统配置 */}
        {system && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">系统配置</h2>
            <div className="space-y-3">
              {[
                { label: '数据目录', value: system.data_dir },
                { label: '版本', value: system.version },
                { label: 'WebUI 状态', value: system.webui_enabled ? '已启用' : '未启用' },
                { label: 'WebUI 端口', value: String(system.webui_port) },
                { label: 'Gateway 状态', value: system.gateway_status },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-sm text-gray-500">{label}</span>
                  <span className="text-sm font-medium text-gray-900">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
