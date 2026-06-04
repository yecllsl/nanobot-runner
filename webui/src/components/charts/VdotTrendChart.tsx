import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import type { VdotTrendItem } from '../../types/api';

interface VdotTrendChartProps {
  data: VdotTrendItem[];
}

export default function VdotTrendChart({ data }: VdotTrendChartProps) {
  if (data.length === 0) {
    return <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">暂无VDOT数据</div>;
  }

  const avgVdot = data.reduce((sum, item) => sum + item.vdot, 0) / data.length;
  const chartData = data.map((item) => ({
    date: item.date.slice(5),
    vdot: item.vdot,
    fullDate: item.date,
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis domain={['dataMin - 1', 'dataMax + 1']} tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <Tooltip formatter={(value: number) => [value.toFixed(1), 'VDOT']} />
          <ReferenceLine y={avgVdot} stroke="#9ca3af" strokeDasharray="5 5"
            label={{ value: `均值 ${avgVdot.toFixed(1)}`, position: 'insideTopRight', fontSize: 11, fill: '#9ca3af' }} />
          <Line type="monotone" dataKey="vdot" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
