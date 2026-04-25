'use client';

import { useState } from 'react';
import { ChevronDownIcon, ChevronRightIcon } from 'lucide-react';
import type { InvestigationResult } from '@/lib/types';

export function AgentReasoning({ investigation }: { investigation: InvestigationResult }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-md border border-border">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-accent/50"
      >
        <span>Agent Reasoning Details</span>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{investigation.iterations_used} iterations · ${investigation.cost_usd.toFixed(4)} · {investigation.duration_seconds.toFixed(1)}s</span>
          {open ? <ChevronDownIcon className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-border p-4 space-y-3">
          <div className="text-xs text-muted-foreground">
            <span className="font-medium">Tools executed:</span>{' '}
            {investigation.tools_executed_summary.join(', ') || 'none'}
          </div>

          {Object.entries(investigation.checklist_completion).length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">Checklist completion:</p>
              <ul className="space-y-1">
                {Object.entries(investigation.checklist_completion).map(([q, done]) => (
                  <li key={q} className="flex items-start gap-2 text-xs">
                    <span className={done ? 'text-resolved' : 'text-muted-foreground'}>
                      {done ? '✓' : '○'}
                    </span>
                    <span className={done ? '' : 'text-muted-foreground'}>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
