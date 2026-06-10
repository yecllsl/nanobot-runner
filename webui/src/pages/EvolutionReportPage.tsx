import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { getEvolutionReport, type EvolutionReport } from '../api/evolution';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function EvolutionReportPage() {
  const { month } = useParams<{ month: string }>();
  const { data: report, loading, execute: fetchReport } = useApi<EvolutionReport, [string]>(getEvolutionReport);

  useEffect(() => {
    if (month) fetchReport(month);
  }, [month, fetchReport]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/evolution" className="text-gray-400 hover:text-gray-600 transition-colors">
          &larr; 返回
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">进化报告 - {month}</h1>
      </div>

      {loading && <LoadingSpinner />}

      {report && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="text-center">
              <p className="text-sm text-gray-500">报告ID</p>
              <p className="text-lg font-bold text-gray-900">{report.report_id}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">月份</p>
              <p className="text-lg font-bold text-gray-900">{report.month}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">总决策数</p>
              <p className="text-lg font-bold text-primary-600">{report.total_decisions}</p>
            </div>
          </div>

          <pre className="bg-gray-50 rounded-lg p-4 text-xs text-gray-700 overflow-auto max-h-96">
            {JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
