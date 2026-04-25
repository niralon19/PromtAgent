import Link from 'next/link';
import { SeverityBadge } from '@/components/common/SeverityBadge';
import { CategoryBadge } from '@/components/common/CategoryBadge';
import { ConfidenceBar } from '@/components/common/ConfidenceBar';
import { RelativeTime } from '@/components/common/RelativeTime';
import { cn } from '@/lib/utils';
import type { Incident } from '@/lib/types';

const STATUS_COLOR: Record<string, string> = {
  open: 'border-l-warning',
  investigating: 'border-l-investigating',
  resolved: 'border-l-resolved',
  false_positive: 'border-l-muted-foreground',
  acknowledged: 'border-l-info',
};

export function IncidentRow({ incident }: { incident: Incident }) {
  return (
    <Link
      href={`/incidents/${incident.id}`}
      className={cn(
        'flex items-center gap-4 rounded-md border-l-4 bg-card px-4 py-3 transition-colors hover:bg-accent',
        STATUS_COLOR[incident.status] ?? 'border-l-border',
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 truncate">
          <span className="font-medium text-sm truncate">{incident.hostname}</span>
          {incident.alert && <SeverityBadge severity={incident.alert.severity} />}
          <CategoryBadge category={incident.category} />
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground truncate">
          {incident.alert?.alertname ?? '—'}{' '}
          {incident.alert?.annotations?.summary && `· ${incident.alert.annotations.summary}`}
        </p>
      </div>

      {incident.confidence != null && (
        <div className="w-28 shrink-0">
          <ConfidenceBar value={incident.confidence} />
        </div>
      )}

      <div className="shrink-0 text-right">
        <span
          className={cn(
            'inline-block rounded-full px-2 py-0.5 text-xs',
            incident.status === 'investigating' ? 'bg-investigating/15 text-investigating' : 'bg-muted text-muted-foreground',
          )}
        >
          {incident.status}
        </span>
        <div className="mt-0.5">
          <RelativeTime iso={incident.created_at} />
        </div>
      </div>
    </Link>
  );
}
