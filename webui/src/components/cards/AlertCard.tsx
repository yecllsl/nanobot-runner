interface AlertCardProps {
  level: 'warning' | 'danger' | 'info';
  title: string;
  message: string;
}

const levelStyles: Record<string, string> = {
  warning: 'bg-yellow-50 border-yellow-300 text-yellow-800',
  danger: 'bg-red-50 border-red-300 text-red-800',
  info: 'bg-blue-50 border-blue-300 text-blue-800',
};

const levelIcons: Record<string, string> = {
  warning: '⚠️',
  danger: '🚨',
  info: 'ℹ️',
};

export default function AlertCard({ level, title, message }: AlertCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${levelStyles[level]}`}>
      <div className="flex items-start gap-2">
        <span className="text-lg">{levelIcons[level]}</span>
        <div>
          <p className="font-semibold">{title}</p>
          <p className="text-sm mt-0.5 opacity-90">{message}</p>
        </div>
      </div>
    </div>
  );
}
