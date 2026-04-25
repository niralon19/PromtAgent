'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  ActivityIcon,
  BarChart2Icon,
  BookOpenIcon,
  ZapIcon,
  ServerIcon,
} from 'lucide-react';

const NAV = [
  { href: '/live', label: 'Live Ops', icon: ActivityIcon },
  { href: '/performance', label: 'Performance', icon: BarChart2Icon },
  { href: '/knowledge', label: 'Knowledge', icon: BookOpenIcon },
  { href: '/autonomy', label: 'Autonomy', icon: ZapIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <ServerIcon className="h-5 w-5 text-primary" />
        <span className="font-semibold text-sm tracking-tight">NOC Center</span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
              pathname.startsWith(href)
                ? 'bg-accent text-accent-foreground font-medium'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
