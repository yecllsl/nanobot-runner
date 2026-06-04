import { TIME_RANGE_OPTIONS } from '../../utils/constants';

interface TimeRangeSelectorProps {
  value: number;
  onChange: (days: number) => void;
}

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-1">
      {TIME_RANGE_OPTIONS.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
            value === option.value
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
