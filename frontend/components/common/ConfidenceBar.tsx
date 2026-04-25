import { cn } from '@/lib/utils';

interface Props {
  value: number; // 0-100
  showLabel?: boolean;
}

export function ConfidenceBar({ value, showLabel = true }: Props) {
  const color =
    value >= 80 ? 'bg-resolved' : value >= 50 ? 'bg-warning' : 'bg-critical';

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-muted">
        <div
          className={cn('h-1.5 rounded-full transition-all', color)}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs tabular-nums text-muted-foreground w-8 text-right">{value}%</span>
      )}
    </div>
  );
}
