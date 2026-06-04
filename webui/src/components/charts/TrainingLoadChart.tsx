import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts';
import type { TrainingLoadTrendItem } from '../../types/api';

interface TrainingLoadChartProps {
  data: TrainingLoadTrendItem[];
}

export default function TrainingLoadChart({ data }: TrainingLoadChartProps) {
  if (data.length === 0) {
    return <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">暂无训练负荷数据</div>;
  }

  const chartData = data.map((item) => ({
    date: item.date.slice(5),
    atl: Number(item.atl.toFixed(1)),
    ctl: Number(item.ctl.toFixed(1)),
    tsb: Number(item.tsb.toFixed(1)),
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <Tooltip formatter={(value: number, name: string) => {
            const labels: Record<string, string> = { atl: 'ATL', ctl: 'CTL', tsb: 'TSB' };
            return [value.toFixed(1), labels[name] || name];
          }} />
          <Legend formatter={(value: string) => {
            const labels: Record<string, string> = { atl: 'ATL (急性)', ctl: 'CTL (慢性)', tsb: 'TSB (平衡)' };
            return labels[value] || value;
          }} />
          <ReferenceLine y={0} stroke="#d1d5db" />
          <Area type="monotone" dataKey="atl" stroke="#f97316" fill="#fed7aa" fillOpacity={0.5} strokeWidth={2} />
          <Area type="monotone" dataKey="ctl" stroke="#3b82f6" fill="#bfdbfe" fillOpacity={0.5} strokeWidth={2} />
          <Area type="monotone" dataKey="tsb" stroke="#10b981" fill="#a7f3d0" fillOpacity={0.3} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
