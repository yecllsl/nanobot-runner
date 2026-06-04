interface StatusCardProps {
  title: string;
  status: string;
  description: string;
  statusColor?: string;
}

export default function StatusCard({ title, status, description, statusColor = 'text-gray-900' }: StatusCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 lg:p-5">
      <p className="text-sm text-gray-500 font-medium">{title}</p>
      <p className={`mt-1 text-xl font-bold ${statusColor}`}>{status}</p>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
    </div>
  );
}
