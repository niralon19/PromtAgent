import { PerformanceDashboard } from './PerformanceDashboard';

export const metadata = { title: 'Performance — NOC Center' };

export default function PerformancePage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Performance</h1>
        <p className="text-sm text-muted-foreground">Agent accuracy, cost, and autonomy readiness</p>
      </div>
      <PerformanceDashboard />
    </div>
  );
}
