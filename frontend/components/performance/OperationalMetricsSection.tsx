interface Props {
  data: Record<string, unknown>;
}

export function OperationalMetricsSection({ data }: Props) {
  return (
    <div className="rounded-md border border-border bg-card p-4 space-y-4">
      <h3 className="font-semibold text-sm">Operational Metrics</h3>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Metric label="Total Agent Runs" value={data.total_runs} />
        <Metric label="Completed" value={data.completed_runs} />
        <Metric label="Failed" value={data.failed_runs} />
        <Metric label="Total Cost" value={data.total_cost_usd != null ? `$${data.total_cost_usd}` : '—'} />
        <Metric label="Avg Iterations" value={data.avg_iterations} />
        <Metric label="Avg Duration" value={data.avg_duration_seconds != null ? `${data.avg_duration_seconds}s` : '—'} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <span className="text-2xl font-bold">{value != null ? String(value) : '—'}</span>
    </div>
  );
}
