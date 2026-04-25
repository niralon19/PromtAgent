'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAutonomyTiers, toggleKillSwitch } from '@/lib/api';
import { cn } from '@/lib/utils';
import { ShieldAlertIcon, ShieldCheckIcon } from 'lucide-react';

export function AutonomyDashboard() {
  const qc = useQueryClient();

  const { data: tiers, isLoading } = useQuery({
    queryKey: ['autonomy', 'tiers'],
    queryFn: getAutonomyTiers,
    staleTime: 30_000,
  });

  const { data: killStatus } = useQuery({
    queryKey: ['autonomy', 'kill-switch'],
    queryFn: () => fetch('/api/v1/autonomy/kill-switch').then((r) => r.json()),
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  const killMutation = useMutation({
    mutationFn: (enabled: boolean) => toggleKillSwitch(enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['autonomy', 'kill-switch'] });
    },
  });

  const killEnabled = killStatus?.kill_switch_enabled ?? false;

  return (
    <div className="space-y-6">
      {/* Kill Switch */}
      <div
        className={cn(
          'flex items-center justify-between rounded-md border p-4',
          killEnabled ? 'border-red-500/50 bg-red-500/5' : 'border-resolved/30 bg-resolved/5',
        )}
      >
        <div className="flex items-center gap-3">
          {killEnabled ? (
            <ShieldAlertIcon className="h-5 w-5 text-red-500" />
          ) : (
            <ShieldCheckIcon className="h-5 w-5 text-resolved" />
          )}
          <div>
            <p className="font-semibold text-sm">Global Kill Switch</p>
            <p className="text-xs text-muted-foreground">
              {killEnabled
                ? 'Autonomous execution is DISABLED. All decisions go to shadow mode.'
                : 'Autonomous execution is ENABLED for qualifying actions.'}
            </p>
          </div>
        </div>
        <button
          onClick={() => killMutation.mutate(!killEnabled)}
          className={cn(
            'rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
            killEnabled
              ? 'bg-resolved text-white hover:bg-resolved/90'
              : 'bg-red-500 text-white hover:bg-red-500/90',
          )}
        >
          {killEnabled ? 'Enable Autonomy' : 'Disable Autonomy'}
        </button>
      </div>

      {/* Tier Table */}
      <div>
        <h3 className="mb-3 font-semibold text-sm">Action Tier Assignments</h3>
        {isLoading ? (
          <div className="text-sm text-muted-foreground animate-pulse">Loading…</div>
        ) : !tiers?.length ? (
          <div className="rounded-md border border-border p-6 text-center text-sm text-muted-foreground">
            No autonomous tiers configured. Use the Performance page to promote actions.
          </div>
        ) : (
          <div className="rounded-md border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Action</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-muted-foreground">Tier</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Promoted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(tiers as Record<string, unknown>[]).map((row) => (
                  <tr key={row.action_key as string} className="hover:bg-accent/30">
                    <td className="px-3 py-2 font-mono text-xs">{row.action_key as string}</td>
                    <td className="px-3 py-2 text-center">
                      <span
                        className={cn(
                          'rounded-full px-2 py-0.5 text-xs font-medium',
                          (row.autonomous_tier as number) === 0
                            ? 'bg-muted text-muted-foreground'
                            : (row.autonomous_tier as number) === 1
                            ? 'bg-warning/15 text-warning'
                            : 'bg-resolved/15 text-resolved',
                        )}
                      >
                        Tier {row.autonomous_tier as number}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">
                      {row.promoted_at ? new Date(row.promoted_at as string).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
