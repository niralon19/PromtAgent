import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { getIncident } from '@/lib/api';
import { useWebSocket } from '@/components/providers/WebSocketProvider';

export function useIncident(id: string) {
  const qc = useQueryClient();
  const { subscribe } = useWebSocket();

  const query = useQuery({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id),
    enabled: !!id,
  });

  useEffect(() => {
    const unsub = subscribe<{ incident_id: string }>('incident.updated', (e) => {
      if (e.data.incident_id === id) qc.invalidateQueries({ queryKey: ['incident', id] });
    });
    const unsub2 = subscribe<{ incident_id: string }>('investigation.completed', (e) => {
      if (e.data.incident_id === id) qc.invalidateQueries({ queryKey: ['incident', id] });
    });
    return () => {
      unsub();
      unsub2();
    };
  }, [id, qc, subscribe]);

  return query;
}
