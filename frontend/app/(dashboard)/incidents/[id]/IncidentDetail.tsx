'use client';

import { useIncident } from '@/hooks/useIncident';
import { IncidentHeader } from '@/components/incident/Header';
import { AnalysisPanel } from '@/components/incident/analysis/AnalysisPanel';
import { IKBContextPanel } from '@/components/incident/context/IKBContextPanel';
import { ActionBar } from '@/components/incident/ActionBar';
import { AgentReasoning } from '@/components/incident/agent/AgentReasoning';

export function IncidentDetail({ id }: { id: string }) {
  const { data: incident, isLoading, isError } = useIncident(id);

  if (isLoading) return <div className="text-sm text-muted-foreground animate-pulse">Loading…</div>;
  if (isError || !incident) return <div className="text-sm text-red-500">Incident not found.</div>;

  return (
    <div className="space-y-6">
      <IncidentHeader incident={incident} />
      <ActionBar incident={incident} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          {incident.investigation ? (
            <>
              <AnalysisPanel investigation={incident.investigation} />
              <AgentReasoning investigation={incident.investigation} />
            </>
          ) : (
            <div className="rounded-md border border-border p-6 text-center text-sm text-muted-foreground">
              {incident.status === 'investigating'
                ? '🔍 Investigation in progress…'
                : 'No investigation data yet.'}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <IKBContextPanel incident={incident} />
        </aside>
      </div>
    </div>
  );
}
