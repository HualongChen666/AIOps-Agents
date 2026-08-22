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
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { error: showError } = useToast();

  const connect = useCallback(() => {
    if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = (event) => {
        setIsConnected(true);
        setIsConnecting(false);
        setReconnectAttempts(0);
        setError(null);
        onOpen?.(event);
      };

      ws.onmessage = (event) => {
        onMessage?.(event);
      };

      ws.onerror = (event) => {
        const err = new Error('WebSocket connection error');
        setError(err);
        setIsConnected(false);
        setIsConnecting(false);
        onError?.(event);
        showError('WebSocket连接错误');
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        setIsConnecting(false);
        onClose?.(event);

        // 自动重连
        if (enabled && reconnectAttempts < maxReconnectAttempts) {
          setReconnectAttempts((prev) => prev + 1);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          showError('WebSocket重连失败，已达到最大重连次数');
        }
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create WebSocket');
      setError(error);
      setIsConnecting(false);
      onError?.(new Event('error'));
    }
  }, [url, enabled, reconnectInterval, maxReconnectAttempts, reconnectAttempts, onMessage, onError, onOpen, onClose, showError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    setReconnectAttempts(0);
  }, []);

  const send = useCallback((data: string | object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    } else {
      showError('WebSocket未连接，无法发送消息');
    }
  }, [showError]);

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
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { error: showError } = useToast();

  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = (event) => {
        setIsConnected(true);
        setIsConnecting(false);
        setReconnectAttempts(0);
        setError(null);
        onOpen?.(event);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onEvent?.({ type: 'message', data });
        } catch (err) {
          onEvent?.({ type: 'message', data: event.data });
        }
      };

      eventSource.onerror = (event) => {
        const err = new Error('SSE connection error');
        setError(err);
        setIsConnected(false);
        setIsConnecting(false);
        onError?.(event);
        showError('SSE连接错误');

        // EventSource会自动重连，但我们需要手动处理关闭
        if (eventSource.readyState === EventSource.CLOSED) {
          eventSourceRef.current = null;

          if (enabled && reconnectAttempts < maxReconnectAttempts) {
            setReconnectAttempts((prev) => prev + 1);
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, reconnectInterval);
          } else if (reconnectAttempts >= maxReconnectAttempts) {
            showError('SSE重连失败，已达到最大重连次数');
          }
        }
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create EventSource');
      setError(error);
      setIsConnecting(false);
      onError?.(new Event('error'));
    }
  }, [url, enabled, reconnectInterval, maxReconnectAttempts, reconnectAttempts, onEvent, onError, onOpen, onClose, showError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    setReconnectAttempts(0);
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