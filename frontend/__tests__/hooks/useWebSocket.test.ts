import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket, useSSE, useRealtimeData } from '@/hooks/useWebSocket';

// Mock the toast hook
jest.mock('@/hooks/useEnhancements', () => ({
  useToast: jest.fn(() => ({
    error: jest.fn(),
  })),
}));

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should connect when enabled', () => {
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com', { enabled: true }));

    expect(result.current.isConnecting).toBe(true);
  });

  it('should not connect when disabled', () => {
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    renderHook(() => useWebSocket('ws://test.com', { enabled: false }));

    expect(global.WebSocket).not.toHaveBeenCalled();
  });

  it('should set connected state on open', () => {
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.isConnecting).toBe(false);
  });

  it('should call onMessage callback when message received', () => {
    const onMessage = jest.fn();
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    renderHook(() => useWebSocket('ws://test.com', { onMessage }));

    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(new MessageEvent('message', { data: 'test' }));
      }
    });

    expect(onMessage).toHaveBeenCalled();
  });

  it('should handle connection error', () => {
    const onError = jest.fn();
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com', { onError }));

    act(() => {
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror(new Event('error'));
      }
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).not.toBeNull();
    expect(onError).toHaveBeenCalled();
  });

  it('should handle connection close', () => {
    const onClose = jest.fn();
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com', { onClose }));

    act(() => {
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose(new Event('close'));
      }
    });

    expect(result.current.isConnected).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });

  it('should send message when connected', () => {
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
    });

    act(() => {
      result.current.send('test message');
    });

    expect(mockWebSocket.send).toHaveBeenCalledWith('test message');
  });

  it('should not send message when not connected', () => {
    const mockWebSocket = {
      readyState: WebSocket.CLOSED,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      result.current.send('test message');
    });

    expect(mockWebSocket.send).not.toHaveBeenCalled();
  });

  it('should disconnect manually', () => {
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      result.current.disconnect();
    });

    expect(mockWebSocket.close).toHaveBeenCalled();
    expect(result.current.isConnected).toBe(false);
  });

  it('should reconnect on close with auto-reconnect', () => {
    jest.useFakeTimers();
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    renderHook(() => useWebSocket('ws://test.com', { reconnectInterval: 5000 }));

    act(() => {
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen(new Event('open'));
      }
    });

    act(() => {
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose(new Event('close'));
      }
    });

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(global.WebSocket).toHaveBeenCalledTimes(2);
    jest.useRealTimers();
  });

  it('should stop reconnecting after max attempts', () => {
    jest.useFakeTimers();
    const mockWebSocket = {
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      send: jest.fn(),
      close: jest.fn(),
    };

    global.WebSocket = jest.fn(() => mockWebSocket) as any;

    const { result } = renderHook(() => useWebSocket('ws://test.com', {
      reconnectInterval: 1000,
      maxReconnectAttempts: 3,
    }));

    // Simulate multiple connection failures
    for (let i = 0; i < 5; i++) {
      act(() => {
        if (mockWebSocket.onclose) {
          mockWebSocket.onclose(new Event('close'));
        }
        jest.advanceTimersByTime(1000);
      });
    }

    expect(result.current.reconnectAttempts).toBe(3);
    jest.useRealTimers();
  });
});

describe('useSSE', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useSSE('/api/sse'));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should connect when enabled', () => {
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    const { result } = renderHook(() => useSSE('/api/sse', { enabled: true }));

    expect(result.current.isConnecting).toBe(true);
  });

  it('should not connect when disabled', () => {
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    renderHook(() => useSSE('/api/sse', { enabled: false }));

    expect(global.EventSource).not.toHaveBeenCalled();
  });

  it('should set connected state on open', () => {
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    const { result } = renderHook(() => useSSE('/api/sse'));

    act(() => {
      if (mockEventSource.onopen) {
        mockEventSource.onopen(new Event('open'));
      }
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.isConnecting).toBe(false);
  });

  it('should call onEvent callback when message received', () => {
    const onEvent = jest.fn();
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    renderHook(() => useSSE('/api/sse', { onEvent }));

    act(() => {
      if (mockEventSource.onmessage) {
        mockEventSource.onmessage(new MessageEvent('message', { data: JSON.stringify({ test: 'data' }) }));
      }
    });

    expect(onEvent).toHaveBeenCalledWith({ type: 'message', data: { test: 'data' } });
  });

  it('should handle connection error', () => {
    const onError = jest.fn();
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    const { result } = renderHook(() => useSSE('/api/sse', { onError }));

    act(() => {
      if (mockEventSource.onerror) {
        mockEventSource.onerror(new Event('error'));
      }
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).not.toBeNull();
    expect(onError).toHaveBeenCalled();
  });

  it('should disconnect manually', () => {
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    const { result } = renderHook(() => useSSE('/api/sse'));

    act(() => {
      result.current.disconnect();
    });

    expect(mockEventSource.close).toHaveBeenCalled();
    expect(result.current.isConnected).toBe(false);
  });

  it('should handle non-JSON message data', () => {
    const onEvent = jest.fn();
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    renderHook(() => useSSE('/api/sse', { onEvent }));

    act(() => {
      if (mockEventSource.onmessage) {
        mockEventSource.onmessage(new MessageEvent('message', { data: 'plain text' }));
      }
    });

    expect(onEvent).toHaveBeenCalledWith({ type: 'message', data: 'plain text' });
  });
});

describe('useRealtimeData', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with null data', () => {
    const { result } = renderHook(() => useRealtimeData<string>('/api/sse'));

    expect(result.current.data).toBeNull();
    expect(result.current.lastUpdate).toBeNull();
  });

  it('should update data on message event', () => {
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    const { result } = renderHook(() => useRealtimeData<{ value: string }>('/api/sse'));

    act(() => {
      if (mockEventSource.onopen) {
        mockEventSource.onopen(new Event('open'));
      }
    });

    act(() => {
      if (mockEventSource.onmessage) {
        mockEventSource.onmessage(
          new MessageEvent('message', { data: JSON.stringify({ value: 'test' }) })
        );
      }
    });

    expect(result.current.data).toEqual({ value: 'test' });
    expect(result.current.lastUpdate).not.toBeNull();
  });

  it('should update data on alert event', () => {
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    const { result } = renderHook(() => useRealtimeData<{ alert: string }>('/api/sse'));

    act(() => {
      if (mockEventSource.onopen) {
        mockEventSource.onopen(new Event('open'));
      }
    });

    act(() => {
      if (mockEventSource.onmessage) {
        mockEventSource.onmessage(
          new MessageEvent('message', { data: JSON.stringify({ type: 'alert', alert: 'test' }) })
        );
      }
    });

    expect(result.current.data).toEqual({ type: 'alert', alert: 'test' });
  });

  it('should call custom onEvent callback', () => {
    const onEvent = jest.fn();
    const mockEventSource = {
      readyState: EventSource.OPEN,
      onopen: null,
      onmessage: null,
      onerror: null,
      close: jest.fn(),
    };

    global.EventSource = jest.fn(() => mockEventSource) as any;

    renderHook(() => useRealtimeData<string>('/api/sse', { onEvent }));

    act(() => {
      if (mockEventSource.onopen) {
        mockEventSource.onopen(new Event('open'));
      }
    });

    act(() => {
      if (mockEventSource.onmessage) {
        mockEventSource.onmessage(new MessageEvent('message', { data: 'test' }));
      }
    });

    expect(onEvent).toHaveBeenCalled();
  });
});
