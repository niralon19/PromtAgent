import { ConfidenceBar } from '@/components/common/ConfidenceBar';

interface Props {
  data: Record<string, unknown>;
}

export function QualityMetricsSection({ data }: Props) {
  const accuracy = data.hypothesis_accuracy_pct as number | null;
  const avgConf = data.avg_confidence as number | null;
  const avgRes = data.avg_resolution_minutes as number | null;
  const evaluated = data.evaluated_count as number;
  const fps = data.false_positive_count as number;
  const total = data.total_incidents as number;

  return (
    <div className="rounded-md border border-border bg-card p-4 space-y-4">
      <h3 className="font-semibold text-sm">Quality Metrics</h3>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Metric label="Hypothesis Accuracy">
          {accuracy != null ? (
            <div className="space-y-1">
              <span className="text-2xl font-bold">{accuracy}%</span>
              <ConfidenceBar value={accuracy} showLabel={false} />
            </div>
          ) : (
            <span className="text-muted-foreground text-sm">No data</span>
          )}
        </Metric>

        <Metric label="Avg Confidence">
          {avgConf != null ? (
            <span className="text-2xl font-bold">{avgConf}%</span>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </Metric>

        <Metric label="Avg Resolution">
          {avgRes != null ? (
            <span className="text-2xl font-bold">{Math.round(avgRes as number)}m</span>
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          )}
        </Metric>

        <Metric label="Evaluated Incidents">
          <span className="text-2xl font-bold">{evaluated ?? 0}</span>
        </Metric>

        <Metric label="False Positives">
          <span className="text-2xl font-bold">{fps ?? 0}</span>
        </Metric>

        <Metric label="Total Incidents">
          <span className="text-2xl font-bold">{total ?? 0}</span>
        </Metric>
      </div>
    </div>
  );
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      {children}
    </div>
  );
}
