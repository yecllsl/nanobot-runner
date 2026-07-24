import { useState, useRef, ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { importData, type ImportResponse } from '../api/import';
import LoadingSpinner from '../components/common/LoadingSpinner';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_FILES = 50;

export default function ImportPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [force, setForce] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, loading, error, execute } = useApi<ImportResponse, [File[], boolean]>(importData);

  // 文件选择处理：校验类型与大小
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFileError(null);
    const files = Array.from(e.target.files ?? []);
    if (files.length > MAX_FILES) {
      setFileError(`文件数量超过上限 ${MAX_FILES} 个`);
      return;
    }
    const invalidType = files.find((f) => !f.name.toLowerCase().endsWith('.fit'));
    if (invalidType) {
      setFileError(`仅支持 .fit 文件: ${invalidType.name}`);
      return;
    }
    const oversize = files.find((f) => f.size > MAX_FILE_SIZE);
    if (oversize) {
      setFileError(`文件过大（>50MB）: ${oversize.name}`);
      return;
    }
    setSelectedFiles(files);
  };

  const handleImport = () => {
    if (selectedFiles.length === 0) return;
    execute(selectedFiles, force);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  };

  // 状态颜色映射
  const statusColor = (status: string) => {
    if (status === 'added') return 'text-green-600';
    if (status === 'skipped') return 'text-yellow-600';
    return 'text-red-600';
  };
  const statusIcon = (status: string) => {
    if (status === 'added') return '✅';
    if (status === 'skipped') return '⏭️';
    return '❌';
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">数据导入</h2>

      {/* 文件选择区 */}
      <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <div className="flex items-center gap-4">
          <input
            ref={inputRef}
            type="file"
            accept=".fit"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={() => inputRef.current?.click()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            选择 .fit 文件
          </button>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="rounded"
            />
            强制重新导入（跳过去重）
          </label>
        </div>

        {/* 已选文件列表 */}
        {selectedFiles.length > 0 && (
          <div className="space-y-1">
            <p className="text-sm text-gray-500">已选文件 ({selectedFiles.length}):</p>
            <ul className="max-h-40 overflow-y-auto space-y-1">
              {selectedFiles.map((f, i) => (
                <li key={i} className="text-sm text-gray-700">
                  • {f.name} <span className="text-gray-400">({formatSize(f.size)})</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {fileError && <p className="text-sm text-red-600">{fileError}</p>}

        <button
          onClick={handleImport}
          disabled={selectedFiles.length === 0 || loading}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? '导入中...' : '开始导入'}
        </button>
      </section>

      {/* 导入结果区 */}
      {loading && <LoadingSpinner />}
      {error && <p className="text-red-600">导入失败: {error}</p>}

      {data && (
        <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <h3 className="font-medium text-gray-900 border-b pb-2">导入结果</h3>
          <ul className="space-y-1">
            {data.results.map((r, i) => (
              <li key={i} className={`text-sm ${statusColor(r.status)}`}>
                {statusIcon(r.status)} {r.filename} — {r.message}
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-4 pt-2 border-t text-sm">
            <span className="text-green-600">成功 {data.summary.added}</span>
            <span className="text-yellow-600">跳过 {data.summary.skipped}</span>
            <span className="text-red-600">错误 {data.summary.errors}</span>
            <Link to="/activities" className="ml-auto text-primary-600 hover:underline">
              查看活动列表 →
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
