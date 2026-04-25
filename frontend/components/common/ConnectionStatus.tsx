'use client';

import { useWebSocket } from '@/components/providers/WebSocketProvider';
import { cn } from '@/lib/utils';

export function ConnectionStatus() {
  const { readyState } = useWebSocket();
  const connected = readyState === WebSocket.OPEN;

  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span
        className={cn(
          'inline-block h-2 w-2 rounded-full',
          connected ? 'bg-resolved' : 'bg-critical',
        )}
      />
      {connected ? 'Live' : 'Disconnected'}
    </div>
  );
}
