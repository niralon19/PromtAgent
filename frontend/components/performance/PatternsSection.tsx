import { useRecentPatterns } from '@/hooks/useMetrics';

export function PatternsSection() {
  const { data, isLoading } = useRecentPatterns();

  return (
    <div className="rounded-md border border-border bg-card p-4 space-y-3">
      <h3 className="font-semibold text-sm">Recurring Patterns (90d)</h3>
      {isLoading && <div className="text-sm text-muted-foreground animate-pulse">Loading…</div>}
      {data && data.length === 0 && (
        <p className="text-sm text-muted-foreground">No recurring patterns detected.</p>
      )}
      {data && data.length > 0 && (
        <ul className="space-y-2">
          {data.slice(0, 10).map((p, i) => (
            <li key={i} className="flex items-center justify-between text-sm">
              <div>
                <span className="font-medium">{p.hostname}</span>
                <span className="ml-2 text-xs text-muted-foreground">{p.category}</span>
              </div>
              <div className="text-right">
                <span className="font-bold tabular-nums">{p.count}</span>
                <span className="ml-1 text-xs text-muted-foreground">incidents</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
