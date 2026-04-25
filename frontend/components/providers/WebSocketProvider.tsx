'use client';

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { subscribe, getReadyState, disconnect, type WSHandler, type Unsubscribe } from '@/lib/websocket';
import type { WSEventType, WSEvent } from '@/lib/types';

interface WSContextValue {
  readyState: number;
  subscribe: <T = unknown>(event: WSEventType | '*', handler: WSHandler<T>) => Unsubscribe;
}

const WSContext = createContext<WSContextValue>({
  readyState: WebSocket.CLOSED,
  subscribe: () => () => {},
});

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);

  useEffect(() => {
    const unsub = subscribe<unknown>('*', () => {
      setReadyState(getReadyState());
    });
    const interval = setInterval(() => setReadyState(getReadyState()), 1500);
    return () => {
      unsub();
      clearInterval(interval);
      disconnect();
    };
  }, []);

  const wrappedSubscribe = useCallback(
    <T = unknown>(event: WSEventType | '*', handler: WSHandler<T>) =>
      subscribe<T>(event, handler),
    [],
  );

  return (
    <WSContext.Provider value={{ readyState, subscribe: wrappedSubscribe }}>
      {children}
    </WSContext.Provider>
  );
}

export const useWebSocket = () => useContext(WSContext);
