'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { acknowledgeIncident, markFalsePositive, escalateIncident } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { Incident } from '@/lib/types';

interface Props {
  incident: Incident;
}

export function ActionBar({ incident }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  const act = async (label: string, fn: () => Promise<unknown>) => {
    setLoading(label);
    try {
      await fn();
      router.refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  const disabled = (label: string) => loading !== null && loading !== label;

  return (
    <div className="flex flex-wrap gap-2">
      {incident.status !== 'acknowledged' && (
        <ActionButton
          label="Acknowledge"
          disabled={disabled('Acknowledge')}
          loading={loading === 'Acknowledge'}
          onClick={() => act('Acknowledge', () => acknowledgeIncident(incident.id))}
          variant="secondary"
        />
      )}

      <ActionButton
        label="False Positive"
        disabled={disabled('False Positive')}
        loading={loading === 'False Positive'}
        onClick={() => act('False Positive', () => markFalsePositive(incident.id))}
        variant="secondary"
      />

      <ActionButton
        label="Escalate to Tier 2"
        disabled={disabled('Escalate')}
        loading={loading === 'Escalate'}
        onClick={() => act('Escalate', () => escalateIncident(incident.id, {}))}
        variant="destructive"
      />
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  disabled,
  loading,
  variant,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  variant: 'primary' | 'secondary' | 'destructive';
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(
        'rounded-md px-3 py-1.5 text-sm transition-colors disabled:opacity-50',
        variant === 'primary' && 'bg-primary text-primary-foreground hover:bg-primary/90',
        variant === 'secondary' && 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground',
        variant === 'destructive' && 'bg-red-500/15 text-red-500 hover:bg-red-500/25',
      )}
    >
      {loading ? '…' : label}
    </button>
  );
}
