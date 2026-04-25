import type { Incident } from '@/lib/types';

interface Props {
  incidents: Incident[];
}

export function StatsBar({ incidents }: Props) {
  const total = incidents.length;
  const critical = incidents.filter((i) => i.alert?.severity === 'critical').length;
  const investigating = incidents.filter((i) => i.status === 'investigating').length;
  const open = incidents.filter((i) => i.status === 'open').length;

  return (
    <div className="flex gap-6 text-sm">
      <Stat label="Total" value={total} />
      <Stat label="Critical" value={critical} color="text-red-500" />
      <Stat label="Investigating" value={investigating} color="text-investigating" />
      <Stat label="Open" value={open} color="text-warning" />
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className={`text-xl font-bold tabular-nums ${color ?? ''}`}>{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}
