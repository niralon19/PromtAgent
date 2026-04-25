import { CheckCircle2Icon } from 'lucide-react';

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
      <CheckCircle2Icon className="mb-4 h-12 w-12 opacity-30" />
      <p className="text-sm">No incidents match the current filters.</p>
    </div>
  );
}
