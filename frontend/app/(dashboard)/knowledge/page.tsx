import { Suspense } from 'react';
import { KnowledgeSearch } from './KnowledgeSearch';

export const metadata = { title: 'Knowledge Explorer — NOC Center' };

export default function KnowledgePage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Knowledge Explorer</h1>
        <p className="text-sm text-muted-foreground">Search resolved incidents, patterns, and insights</p>
      </div>
      <Suspense fallback={<div className="text-sm text-muted-foreground">Loading…</div>}>
        <KnowledgeSearch />
      </Suspense>
    </div>
  );
}
