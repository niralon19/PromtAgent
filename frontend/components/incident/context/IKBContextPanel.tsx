'use client';

import { useQuery } from '@tanstack/react-query';
import { getSimilarIncidents } from '@/lib/api';
import type { Incident } from '@/lib/types';

export function IKBContextPanel({ incident }: { incident: Incident }) {
  const { data: similar } = useQuery({
    queryKey: ['similar', incident.id],
    queryFn: () => getSimilarIncidents(incident.id),
  });

  const enrichment = incident.enrichment as Record<string, unknown> | null;
  const baseline = enrichment?.baseline_analysis as Record<string, unknown> | null;
  const recurrence = enrichment?.recurrence_info as Record<string, unknown> | null;

  return (
    <div className="space-y-4">
      {/* Baseline */}
      {baseline != null && (
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Baseline Analysis
          </h3>
          <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
            <div className="flex justify-between">
              <span>Z-Score</span>
              <span className="font-mono">{(baseline.z_score as number).toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Severity</span>
              <span>{String(baseline.severity_level ?? '')}</span>
            </div>
            <div className="flex justify-between">
              <span>Anomaly</span>
              <span>{baseline.is_anomaly ? 'Yes' : 'No'}</span>
            </div>
          </div>
        </section>
      )}

      {/* Recurrence */}
      {recurrence?.is_recurring === true && (
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Recurrence
          </h3>
          <div className="rounded-md border border-warning/30 bg-warning/5 p-3 text-sm">
            <p>{Number(recurrence.count_last_90d)} similar in last 90 days</p>
            {recurrence.pattern_hint != null && (
              <p className="text-xs text-muted-foreground">{String(recurrence.pattern_hint)}</p>
            )}
          </div>
        </section>
      )}

      {/* Similar */}
      {similar && similar.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Similar Past Incidents
          </h3>
          <ul className="space-y-2">
            {similar.slice(0, 5).map((s) => (
              <li key={s.id} className="flex items-center justify-between text-sm">
                <span>{s.hostname}</span>
                <span className="text-xs text-muted-foreground">
                  {(s.similarity_score * 100).toFixed(0)}% · {s.resolution_category ?? '—'}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
