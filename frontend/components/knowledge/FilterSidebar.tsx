'use client';

import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';
import { cn } from '@/lib/utils';

const CATEGORIES = ['physical', 'data_integrity', 'coupling'];
const RESOLUTIONS = ['process_kill', 'config_fix', 'hardware_replace', 'network_fix', 'escalated', 'false_positive', 'unknown'];

export function FilterSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const set = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (params.get(key) === value) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
      router.replace(`${pathname}?${params.toString()}`);
    },
    [pathname, router, searchParams],
  );

  return (
    <aside className="w-44 shrink-0 space-y-4">
      <FilterGroup
        label="Category"
        options={CATEGORIES}
        active={(v) => searchParams.get('category') === v}
        onToggle={(v) => set('category', v)}
      />
      <FilterGroup
        label="Resolution"
        options={RESOLUTIONS}
        active={(v) => searchParams.get('resolution_category') === v}
        onToggle={(v) => set('resolution_category', v)}
      />
    </aside>
  );
}

function FilterGroup({
  label,
  options,
  active,
  onToggle,
}: {
  label: string;
  options: string[];
  active: (v: string) => boolean;
  onToggle: (v: string) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <ul className="space-y-1">
        {options.map((opt) => (
          <li key={opt}>
            <button
              onClick={() => onToggle(opt)}
              className={cn(
                'w-full rounded-md px-2 py-1 text-left text-xs transition-colors',
                active(opt)
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              {opt.replace(/_/g, ' ')}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
