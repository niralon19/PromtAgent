import { cn } from '@/lib/utils';
import type { IncidentCategory } from '@/lib/types';

const MAP: Record<IncidentCategory, string> = {
  physical: 'bg-orange-500/15 text-orange-500 border-orange-500/30',
  data_integrity: 'bg-purple-500/15 text-purple-500 border-purple-500/30',
  coupling: 'bg-cyan-500/15 text-cyan-500 border-cyan-500/30',
};

export function CategoryBadge({ category }: { category: string }) {
  const cls = MAP[category as IncidentCategory] ?? 'bg-muted text-muted-foreground border-border';
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium', cls)}>
      {category.replace('_', ' ')}
    </span>
  );
}
