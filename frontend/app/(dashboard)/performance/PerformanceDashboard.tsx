'use client';

import { useQualityMetrics, useOperationalMetrics } from '@/hooks/useMetrics';
import { QualityMetricsSection } from '@/components/performance/QualityMetricsSection';
import { OperationalMetricsSection } from '@/components/performance/OperationalMetricsSection';
import { AutonomyTable } from '@/components/performance/AutonomyTable';
import { PatternsSection } from '@/components/performance/PatternsSection';
import { SystemHealthSection } from '@/components/performance/SystemHealthSection';

export function PerformanceDashboard() {
  const { data: quality, isLoading: qLoading } = useQualityMetrics();
  const { data: ops, isLoading: oLoading } = useOperationalMetrics();

  return (
    <div className="space-y-6">
      <SystemHealthSection />

      <div className="grid gap-6 lg:grid-cols-2">
        {qLoading ? (
          <div className="text-sm text-muted-foreground animate-pulse">Loading quality metrics…</div>
        ) : quality ? (
          <QualityMetricsSection data={quality} />
        ) : null}

        {oLoading ? (
          <div className="text-sm text-muted-foreground animate-pulse">Loading operational metrics…</div>
        ) : ops ? (
          <OperationalMetricsSection data={ops} />
        ) : null}
      </div>

      <PatternsSection />

      <div>
        <h3 className="mb-3 font-semibold text-sm">Autonomy Promotion Candidates</h3>
        <AutonomyTable />
      </div>
    </div>
  );
}
