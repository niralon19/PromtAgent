import type { WSEvent, WSEventType } from './types';

export type WSHandler<T = unknown> = (event: WSEvent<T>) => void;
export type Unsubscribe = () => void;

const WS_URL =
  typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`
    : 'ws://localhost:8000/ws';

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
const handlers = new Map<WSEventType | '*', Set<WSHandler>>();

function connect() {
  if (socket && socket.readyState < WebSocket.CLOSING) return;

  socket = new WebSocket(WS_URL);

  socket.onmessage = (msg) => {
    try {
      const event = JSON.parse(msg.data) as WSEvent;
      const typeHandlers = handlers.get(event.event);
      if (typeHandlers) typeHandlers.forEach((h) => h(event));
      const wildcards = handlers.get('*');
      if (wildcards) wildcards.forEach((h) => h(event));
    } catch {
      // ignore malformed messages
    }
  };

  socket.onclose = () => {
    reconnectTimer = setTimeout(connect, 3000);
  };

  socket.onerror = () => {
    socket?.close();
  };
}

export function subscribe<T = unknown>(
  eventType: WSEventType | '*',
  handler: WSHandler<T>,
): Unsubscribe {
  if (!handlers.has(eventType)) handlers.set(eventType, new Set());
  handlers.get(eventType)!.add(handler as WSHandler);
  connect();
  return () => {
    handlers.get(eventType)?.delete(handler as WSHandler);
  };
}

export function getReadyState(): number {
  return socket?.readyState ?? WebSocket.CLOSED;
}

export function disconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  socket?.close();
  socket = null;
}
