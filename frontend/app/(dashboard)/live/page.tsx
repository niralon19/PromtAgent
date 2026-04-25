import { Suspense } from 'react';
import { LiveIncidentsList } from './LiveIncidentsList';

export const metadata = { title: 'Live Operations — NOC Center' };

export default function LivePage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Live Operations</h1>
        <p className="text-sm text-muted-foreground">Real-time incident feed — auto-refreshes every 60s</p>
      </div>
      <Suspense fallback={<div className="text-sm text-muted-foreground">Loading…</div>}>
        <LiveIncidentsList />
      </Suspense>
    </div>
  );
}
