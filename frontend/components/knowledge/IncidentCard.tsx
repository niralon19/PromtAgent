import Link from 'next/link';
import { ConfidenceBar } from '@/components/common/ConfidenceBar';
import { CategoryBadge } from '@/components/common/CategoryBadge';
import { RelativeTime } from '@/components/common/RelativeTime';

interface Props {
  incident: Record<string, unknown>;
}

export function IncidentCard({ incident }: Props) {
  return (
    <Link
      href={`/knowledge/${incident.id}`}
      className="block rounded-md border border-border bg-card p-4 hover:bg-accent/50 transition-colors space-y-2"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{String(incident.hostname ?? '')}</span>
          <CategoryBadge category={String(incident.category ?? '')} />
        </div>
        {incident.created_at != null && <RelativeTime iso={String(incident.created_at)} />}
      </div>

      {incident.hypothesis != null && (
        <p className="text-sm text-muted-foreground line-clamp-2">{String(incident.hypothesis)}</p>
      )}

      <div className="flex items-center justify-between">
        {incident.confidence != null && (
          <div className="w-32">
            <ConfidenceBar value={Number(incident.confidence)} />
          </div>
        )}
        {incident.resolution_category != null && (
          <span className="text-xs text-muted-foreground">
            Resolved: {String(incident.resolution_category).replace(/_/g, ' ')}
          </span>
        )}
      </div>
    </Link>
  );
}
