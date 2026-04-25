'use client';

import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';
import { cn } from '@/lib/utils';

const STATUSES = ['open', 'investigating', 'acknowledged', 'resolved', 'false_positive'];
const CATEGORIES = ['physical', 'data_integrity', 'coupling'];
const SEVERITIES = ['critical', 'warning', 'info'];

export function FilterBar() {
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

  const active = (key: string, val: string) => searchParams.get(key) === val;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <FilterGroup
        label="Status"
        options={STATUSES}
        active={(v) => active('status', v)}
        onToggle={(v) => set('status', v)}
      />
      <FilterGroup
        label="Category"
        options={CATEGORIES}
        active={(v) => active('category', v)}
        onToggle={(v) => set('category', v)}
      />
      <FilterGroup
        label="Severity"
        options={SEVERITIES}
        active={(v) => active('severity', v)}
        onToggle={(v) => set('severity', v)}
      />
    </div>
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
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-muted-foreground">{label}:</span>
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onToggle(opt)}
          className={cn(
            'rounded-full px-2.5 py-0.5 text-xs transition-colors',
            active(opt)
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground',
          )}
        >
          {opt.replace('_', ' ')}
        </button>
      ))}
    </div>
  );
}
