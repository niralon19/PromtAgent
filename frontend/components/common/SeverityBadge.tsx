import { cn } from '@/lib/utils';
import type { Severity } from '@/lib/types';

const MAP: Record<Severity, string> = {
  critical: 'bg-red-500/15 text-red-500 border-red-500/30',
  warning: 'bg-amber-500/15 text-amber-500 border-amber-500/30',
  info: 'bg-blue-500/15 text-blue-500 border-blue-500/30',
};

export function SeverityBadge({ severity }: { severity: string }) {
  const cls = MAP[severity as Severity] ?? 'bg-muted text-muted-foreground border-border';
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium', cls)}>
      {severity}
    </span>
  );
}
