import { AutonomyDashboard } from './AutonomyDashboard';

export const metadata = { title: 'Autonomy — NOC Center' };

export default function AutonomyPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Autonomous Remediation</h1>
        <p className="text-sm text-muted-foreground">
          Graded autonomous execution — tier-gated, circuit-broken, fully audited
        </p>
      </div>
      <AutonomyDashboard />
    </div>
  );
}
