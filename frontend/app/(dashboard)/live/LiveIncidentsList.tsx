'use client';

import { useSearchParams } from 'next/navigation';
import { useIncidents } from '@/hooks/useIncidents';
import { IncidentRow } from '@/components/incident/IncidentRow';
import { FilterBar } from '@/components/incident/FilterBar';
import { StatsBar } from '@/components/incident/StatsBar';
import { EmptyState } from '@/components/incident/EmptyState';

export function LiveIncidentsList() {
  const params = useSearchParams();
  const filters: Record<string, string> = {};
  for (const [k, v] of params.entries()) filters[k] = v;

  const { data, isLoading, isError } = useIncidents(filters);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <StatsBar incidents={data ?? []} />
        <FilterBar />
      </div>

      <div className="space-y-2">
        {isLoading && (
          <div className="text-sm text-muted-foreground animate-pulse">Loading incidents…</div>
        )}
        {isError && (
          <div className="text-sm text-red-500">Failed to load incidents.</div>
        )}
        {data && data.length === 0 && <EmptyState />}
        {data?.map((incident) => (
          <IncidentRow key={incident.id} incident={incident} />
        ))}
      </div>
    </div>
  );
}
