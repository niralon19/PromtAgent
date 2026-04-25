import { SeverityBadge } from '@/components/common/SeverityBadge';
import { CategoryBadge } from '@/components/common/CategoryBadge';
import { RelativeTime } from '@/components/common/RelativeTime';
import type { Incident } from '@/lib/types';

export function IncidentHeader({ incident }: { incident: Incident }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {incident.alert && <SeverityBadge severity={incident.alert.severity} />}
        <CategoryBadge category={incident.category} />
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {incident.status}
        </span>
      </div>
      <h1 className="text-xl font-semibold">
        {incident.alert?.alertname ?? 'Incident'} — {incident.hostname}
      </h1>
      {incident.alert?.annotations?.summary && (
        <p className="text-sm text-muted-foreground">{incident.alert.annotations.summary}</p>
      )}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>ID: {incident.id.slice(0, 8)}…</span>
        <RelativeTime iso={incident.created_at} />
        {incident.alert?.value != null && (
          <span>Value: {incident.alert.value}</span>
        )}
      </div>
    </div>
  );
}
