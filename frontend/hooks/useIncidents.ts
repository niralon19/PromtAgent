import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { getIncidents } from '@/lib/api';
import { useWebSocket } from '@/components/providers/WebSocketProvider';
import type { Incident } from '@/lib/types';

export function useIncidents(filters?: Record<string, string>) {
  const qc = useQueryClient();
  const { subscribe } = useWebSocket();

  const query = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => getIncidents(filters),
    refetchInterval: 60_000,
  });

  useEffect(() => {
    const unsub = subscribe<{ incident: Incident }>('incident.created', () => {
      qc.invalidateQueries({ queryKey: ['incidents'] });
    });
    const unsub2 = subscribe<{ incident: Incident }>('incident.updated', () => {
      qc.invalidateQueries({ queryKey: ['incidents'] });
    });
    return () => {
      unsub();
      unsub2();
    };
  }, [qc, subscribe]);

  return query;
}
