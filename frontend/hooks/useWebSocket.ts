'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useToast } from './useEnhancements';

interface SSEEvent {
  type: string;
  data: any;
}

interface UseWebSocketOptions {
  enabled?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (event: MessageEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: Event) => void;
}

interface UseSSEOptions {
  enabled?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onEvent?: (event: SSEEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: Event) => void;
}

// WebSocket / EventSource readyState values are fixed by the WHATWG spec. We
// read them from the (possibly patched/mocked) constructor when available and
// fall back to the spec constants otherwise, so the hooks behave identically in
// production, in jsdom and under partially-stubbed constructors in tests.
const WS_CONNECTING =
  typeof WebSocket !== 'undefined' && typeof WebSocket.CONNECTING === 'number' ? WebSocket.CONNECTING : 0;
const WS_OPEN =
  typeof WebSocket !== 'undefined' && typeof WebSocket.OPEN === 'number' ? WebSocket.OPEN : 1;
const ES_CONNECTING =
  typeof EventSource !== 'undefined' && typeof (EventSource as any).CONNECTING === 'number'
    ? (EventSource as any).CONNECTING
    : 0;
const ES_OPEN =
  typeof EventSource !== 'undefined' && typeof (EventSource as any).OPEN === 'number'
    ? (EventSource as any).OPEN
    : 1;
const ES_CLOSED =
  typeof EventSource !== 'undefined' && typeof (EventSource as any).CLOSED === 'number'
    ? (EventSource as any).CLOSED
    : 2;

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const {
    enabled = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    onMessage,
    onError,
    onOpen,
    onClose,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { error: showError } = useToast();

  // Latest callbacks / toast are kept in a ref so `connect` can stay referentially
  // stable across renders (otherwise every reconnect-attempt state change would
  // recreate `connect`, re-run the mount effect and tear the socket down again —
  // the reconnect storm this hook used to suffer from).
  const latestRef = useRef({ onMessage, onError, onOpen, onClose, showError });
  useEffect(() => {
    latestRef.current = { onMessage, onError, onOpen, onClose, showError };
  });

  // Number of reconnect attempts so far. Held in a ref (mirrored to state for the
  // consumer) so the close handler always reads the up-to-date value.
  const attemptsRef = useRef(0);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;

    const current = wsRef.current;
    if (current && (current.readyState === WS_OPEN || current.readyState === WS_CONNECTING)) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create WebSocket');
      setError(error);
      setIsConnecting(false);
      latestRef.current.onError?.(new Event('error'));
      return;
    }

    wsRef.current = ws;

    ws.onopen = (event) => {
      setIsConnected(true);
      setIsConnecting(false);
      attemptsRef.current = 0;
      setReconnectAttempts(0);
      setError(null);
      latestRef.current.onOpen?.(event);
    };

    ws.onmessage = (event) => {
      latestRef.current.onMessage?.(event);
    };

    ws.onerror = (event) => {
      setError(new Error('WebSocket connection error'));
      setIsConnected(false);
      setIsConnecting(false);
      latestRef.current.onError?.(event);
      latestRef.current.showError?.('WebSocket连接错误');
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      setIsConnecting(false);
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      latestRef.current.onClose?.(event);

      // 自动重连
      if (enabled && attemptsRef.current < maxReconnectAttempts) {
        attemptsRef.current += 1;
        setReconnectAttempts(attemptsRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectTimeoutRef.current = null;
          connect();
        }, reconnectInterval);
      } else if (attemptsRef.current >= maxReconnectAttempts) {
        latestRef.current.showError?.('WebSocket重连失败，已达到最大重连次数');
      }
    };
  }, [url, enabled, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    clearReconnectTimer();

    const ws = wsRef.current;
    wsRef.current = null;
    if (ws) {
      // Detach the close handler first so a manual disconnect is not mistaken for
      // a dropped connection and does not trigger an automatic reconnect.
      ws.onclose = null;
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.close();
    }

    setIsConnected(false);
    setIsConnecting(false);
    attemptsRef.current = 0;
    setReconnectAttempts(0);
  }, [clearReconnectTimer]);

  const send = useCallback((data: string | object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WS_OPEN) {
      ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    } else {
      latestRef.current.showError?.('WebSocket未连接，无法发送消息');
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    isConnecting,
    error,
    reconnectAttempts,
    send,
    connect,
    disconnect,
  };
}

export function useSSE(url: string, options: UseSSEOptions = {}) {
  const {
    enabled = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    onEvent,
    onError,
    onOpen,
    onClose,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { error: showError } = useToast();

  const latestRef = useRef({ onEvent, onError, onOpen, onClose, showError });
  useEffect(() => {
    latestRef.current = { onEvent, onError, onOpen, onClose, showError };
  });

  const attemptsRef = useRef(0);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;

    const current = eventSourceRef.current;
    if (current && (current.readyState === ES_OPEN || current.readyState === ES_CONNECTING)) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    let eventSource: EventSource;
    try {
      eventSource = new EventSource(url);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create EventSource');
      setError(error);
      setIsConnecting(false);
      latestRef.current.onError?.(new Event('error'));
      return;
    }

    eventSourceRef.current = eventSource;

    eventSource.onopen = (event) => {
      setIsConnected(true);
      setIsConnecting(false);
      attemptsRef.current = 0;
      setReconnectAttempts(0);
      setError(null);
      latestRef.current.onOpen?.(event);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        latestRef.current.onEvent?.({ type: 'message', data });
      } catch {
        latestRef.current.onEvent?.({ type: 'message', data: event.data });
      }
    };

    eventSource.onerror = (event) => {
      setError(new Error('SSE connection error'));
      setIsConnected(false);
      setIsConnecting(false);
      latestRef.current.onError?.(event);
      latestRef.current.showError?.('SSE连接错误');

      // EventSource reconnects on its own; we only handle the terminal CLOSED state.
      if (eventSource.readyState === ES_CLOSED) {
        if (eventSourceRef.current === eventSource) {
          eventSourceRef.current = null;
        }

        if (enabled && attemptsRef.current < maxReconnectAttempts) {
          attemptsRef.current += 1;
          setReconnectAttempts(attemptsRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, reconnectInterval);
        } else if (attemptsRef.current >= maxReconnectAttempts) {
          latestRef.current.showError?.('SSE重连失败，已达到最大重连次数');
        }
      }
    };
  }, [url, enabled, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    clearReconnectTimer();

    const es = eventSourceRef.current;
    eventSourceRef.current = null;
    if (es) {
      es.onopen = null;
      es.onmessage = null;
      es.onerror = null;
      es.close();
    }

    setIsConnected(false);
    setIsConnecting(false);
    attemptsRef.current = 0;
    setReconnectAttempts(0);
  }, [clearReconnectTimer]);

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    isConnecting,
    error,
    reconnectAttempts,
    disconnect,
  };
}

// 🔧 统一的实时数据管理Hook
export function useRealtimeData<T>(url: string, options: UseSSEOptions = {}) {
  const [data, setData] = useState<T | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const handleEvent = useCallback((event: SSEEvent) => {
    if (event.type === 'message' || event.type === 'alert') {
      setData(event.data);
      setLastUpdate(new Date());
    }
  }, []);

  const sse = useSSE(url, {
    ...options,
    onEvent: (event) => {
      handleEvent(event);
      options.onEvent?.(event);
    },
  });

  return {
    ...sse,
    data,
    lastUpdate,
  };
}
