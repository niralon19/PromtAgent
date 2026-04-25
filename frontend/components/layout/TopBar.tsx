'use client';

import { useTheme } from 'next-themes';
import { SunIcon, MoonIcon } from 'lucide-react';
import { ConnectionStatus } from '@/components/common/ConnectionStatus';

export function TopBar() {
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-12 items-center justify-between border-b border-border px-6">
      <div className="text-sm text-muted-foreground">NOC Intelligent Alert Management</div>
      <div className="flex items-center gap-4">
        <ConnectionStatus />
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}
