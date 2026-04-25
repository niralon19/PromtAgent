import { useSystemHealth } from '@/hooks/useMetrics';
import { cn } from '@/lib/utils';

export function SystemHealthSection() {
  const { data } = useSystemHealth();

  const components = [
    { label: 'Database', key: 'database' },
    { label: 'API', key: 'status' },
  ];

  return (
    <div className="rounded-md border border-border bg-card p-4 space-y-3">
      <h3 className="font-semibold text-sm">System Health</h3>
      <div className="flex gap-4">
        {components.map(({ label, key }) => {
          const status = data?.[key] as string | undefined;
          const ok = status === 'ok';
          return (
            <div key={key} className="flex items-center gap-2">
              <span
                className={cn(
                  'h-2 w-2 rounded-full',
                  ok ? 'bg-resolved' : status ? 'bg-critical' : 'bg-muted-foreground',
                )}
              />
              <span className="text-sm">{label}</span>
              <span className="text-xs text-muted-foreground">{status ?? '…'}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
