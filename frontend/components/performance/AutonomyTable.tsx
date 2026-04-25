'use client';

import { useQuery } from '@tanstack/react-query';
import { getAutonomyCandidates } from '@/lib/api';
import { ConfidenceBar } from '@/components/common/ConfidenceBar';

export function AutonomyTable() {
  const { data, isLoading } = useQuery({
    queryKey: ['autonomy', 'candidates'],
    queryFn: getAutonomyCandidates,
    staleTime: 120_000,
  });

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>;
  if (!data?.length)
    return (
      <div className="rounded-md border border-border p-6 text-center text-sm text-muted-foreground">
        No actions qualify for autonomy promotion yet.
      </div>
    );

  return (
    <div className="rounded-md border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Action</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Uses</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Accuracy</th>
            <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Avg Resolution</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((row) => (
            <tr key={row.action_key as string} className="hover:bg-accent/30">
              <td className="px-3 py-2 font-mono text-xs">{row.action_key as string}</td>
              <td className="px-3 py-2 text-right tabular-nums">{row.total_uses as number}</td>
              <td className="px-3 py-2 w-40">
                <ConfidenceBar value={row.accuracy_pct as number} />
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                {row.avg_resolution_minutes != null
                  ? `${Math.round(row.avg_resolution_minutes as number)}m`
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
