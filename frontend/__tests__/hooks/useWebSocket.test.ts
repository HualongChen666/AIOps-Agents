import { renderHook, act } from '@testing-library/react';
import { useWebSocket, useSSE, useRealtimeData } from '@/hooks/useWebSocket';

// Mock the toast hook
jest.mock('@/hooks/useEnhancements', () => ({
  useToast: jest.fn(() => ({
    error: jest.fn(),
  })),
}));

type MockWebSocket = {
  readyState: number;
  onopen: ((ev: Event) => void) | null;
  onmessage: ((ev: MessageEvent) => void) | null;
  onerror: ((ev: Event) => void) | null;
  onclose: ((ev: Event) => void) | null;
  send: jest.Mock;
  close: jest.Mock;
};

type MockEventSource = {
  readyState: number;
  onopen: ((ev: Event) => void) | null;
  onmessage: ((ev: MessageEvent) => void) | null;
  onerror: ((ev: Event) => void) | null;
  close: jest.Mock;
};

const OriginalWebSocket = global.WebSocket;
const OriginalEventSource = global.EventSource;

// Install a spec-compliant WebSocket constructor: the mock instance AND the
// readyState constants (the hook — like any WebSocket client — reads
// WebSocket.OPEN/CONNECTING). The real globals are restored after each test.
function installWebSocket(overrides: Partial<MockWebSocket> = {}) {
  const ws: MockWebSocket = {
    readyState: 1, // OPEN
    onopen: null,
    onmessage: null,
    onerror: null,
    onclose: null,
    send: jest.fn(),
    close: jest.fn(),
    ...overrides,
  };
  const Ctor: any = jest.fn(() => ws);
  Ctor.CONNECTING = 0;
  Ctor.OPEN = 1;
  Ctor.CLOSING = 2;
  Ctor.CLOSED = 3;
  (global as any).WebSocket = Ctor;
  return { ws, Ctor };
}

function installEventSource(overrides: Partial<MockEventSource> = {}) {
  const es: MockEventSource = {
    readyState: 1, // OPEN
    onopen: null,
    onmessage: null,
    onerror: null,
    close: jest.fn(),
    ...overrides,
  };
  const Ctor: any = jest.fn(() => es);
  Ctor.CONNECTING = 0;
  Ctor.OPEN = 1;
  Ctor.CLOSED = 2;
  (global as any).EventSource = Ctor;
  return { es, Ctor };
}

afterEach(() => {
  (global as any).WebSocket = OriginalWebSocket;
  (global as any).EventSource = OriginalEventSource;
  jest.useRealTimers();
});

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with disconnected state', () => {
    // With `enabled: false` the hook performs no connection, so it reports the
    // pristine disconnected state.
    const { result } = renderHook(() => useWebSocket('ws://test.com', { enabled: false }));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should connect when enabled', () => {
    const { Ctor } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com', { enabled: true }));

    expect(Ctor).toHaveBeenCalledTimes(1);
    expect(result.current.isConnecting).toBe(true);
  });

  it('should not connect when disabled', () => {
    const { Ctor } = installWebSocket();

    renderHook(() => useWebSocket('ws://test.com', { enabled: false }));

    expect(Ctor).not.toHaveBeenCalled();
  });

  it('should set connected state on open', () => {
    const { ws } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      ws.onopen?.(new Event('open'));
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.isConnecting).toBe(false);
  });

  it('should call onMessage callback when message received', () => {
    const onMessage = jest.fn();
    const { ws } = installWebSocket();

    renderHook(() => useWebSocket('ws://test.com', { onMessage }));

    act(() => {
      ws.onmessage?.(new MessageEvent('message', { data: 'test' }));
    });

    expect(onMessage).toHaveBeenCalledTimes(1);
    expect(onMessage.mock.calls[0][0].data).toBe('test');
  });

  it('should handle connection error', () => {
    const onError = jest.fn();
    const { ws } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com', { onError }));

    act(() => {
      ws.onerror?.(new Event('error'));
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).not.toBeNull();
    expect(onError).toHaveBeenCalled();
  });

  it('should handle connection close', () => {
    const onClose = jest.fn();
    const { ws } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com', { onClose }));

    act(() => {
      ws.onclose?.(new Event('close'));
    });

    expect(result.current.isConnected).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });

  it('should send message when connected', () => {
    const { ws } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      ws.onopen?.(new Event('open'));
    });

    act(() => {
      result.current.send('test message');
    });

    expect(ws.send).toHaveBeenCalledWith('test message');
  });

  it('should serialise object payloads before sending', () => {
    const { ws } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      ws.onopen?.(new Event('open'));
    });

    act(() => {
      result.current.send({ kind: 'ping' });
    });

    expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ kind: 'ping' }));
  });

  it('should not send message when not connected', () => {
    const { ws } = installWebSocket({ readyState: 3 /* CLOSED */ });

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      result.current.send('test message');
    });

    expect(ws.send).not.toHaveBeenCalled();
  });

  it('should disconnect manually', () => {
    const { ws } = installWebSocket();

    const { result } = renderHook(() => useWebSocket('ws://test.com'));

    act(() => {
      result.current.disconnect();
    });

    expect(ws.close).toHaveBeenCalled();
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
  });

  it('should reconnect on close with auto-reconnect', () => {
    jest.useFakeTimers();
    const { ws, Ctor } = installWebSocket();

    renderHook(() => useWebSocket('ws://test.com', { reconnectInterval: 5000 }));

    act(() => {
      ws.onopen?.(new Event('open'));
    });

    act(() => {
      ws.onclose?.(new Event('close'));
    });

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(Ctor).toHaveBeenCalledTimes(2);
  });

  it('should stop reconnecting after max attempts', () => {
    jest.useFakeTimers();
    const { ws } = installWebSocket();

    const { result } = renderHook(() =>
      useWebSocket('ws://test.com', {
        reconnectInterval: 1000,
        maxReconnectAttempts: 3,
      })
    );

    // Simulate repeated connection drops.
    for (let i = 0; i < 5; i++) {
      act(() => {
        ws.onclose?.(new Event('close'));
      });
      act(() => {
        jest.advanceTimersByTime(1000);
      });
    }

    expect(result.current.reconnectAttempts).toBe(3);
  });
});

describe('useSSE', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useSSE('/api/sse', { enabled: false }));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.isConnecting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should connect when enabled', () => {
    const { Ctor } = installEventSource();

    const { result } = renderHook(() => useSSE('/api/sse', { enabled: true }));

    expect(Ctor).toHaveBeenCalledTimes(1);
    expect(result.current.isConnecting).toBe(true);
  });

  it('should not connect when disabled', () => {
    const { Ctor } = installEventSource();

    renderHook(() => useSSE('/api/sse', { enabled: false }));

    expect(Ctor).not.toHaveBeenCalled();
  });

  it('should set connected state on open', () => {
    const { es } = installEventSource();

    const { result } = renderHook(() => useSSE('/api/sse'));

    act(() => {
      es.onopen?.(new Event('open'));
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.isConnecting).toBe(false);
  });

  it('should call onEvent callback when message received', () => {
    const onEvent = jest.fn();
    const { es } = installEventSource();

    renderHook(() => useSSE('/api/sse', { onEvent }));

    act(() => {
      es.onmessage?.(new MessageEvent('message', { data: JSON.stringify({ test: 'data' }) }));
    });

    expect(onEvent).toHaveBeenCalledWith({ type: 'message', data: { test: 'data' } });
  });

  it('should handle connection error', () => {
    const onError = jest.fn();
    const { es } = installEventSource();

    const { result } = renderHook(() => useSSE('/api/sse', { onError }));

    act(() => {
      es.onerror?.(new Event('error'));
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).not.toBeNull();
    expect(onError).toHaveBeenCalled();
  });

  it('should disconnect manually', () => {
    const { es } = installEventSource();

    const { result } = renderHook(() => useSSE('/api/sse'));

    act(() => {
      result.current.disconnect();
    });

    expect(es.close).toHaveBeenCalled();
    expect(result.current.isConnected).toBe(false);
  });

  it('should handle non-JSON message data', () => {
    const onEvent = jest.fn();
    const { es } = installEventSource();

    renderHook(() => useSSE('/api/sse', { onEvent }));

    act(() => {
      es.onmessage?.(new MessageEvent('message', { data: 'plain text' }));
    });

    expect(onEvent).toHaveBeenCalledWith({ type: 'message', data: 'plain text' });
  });
});

describe('useRealtimeData', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with null data', () => {
    installEventSource();
    const { result } = renderHook(() => useRealtimeData<string>('/api/sse'));

    expect(result.current.data).toBeNull();
    expect(result.current.lastUpdate).toBeNull();
  });

  it('should update data on message event', () => {
    const { es } = installEventSource();

    const { result } = renderHook(() => useRealtimeData<{ value: string }>('/api/sse'));

    act(() => {
      es.onopen?.(new Event('open'));
    });

    act(() => {
      es.onmessage?.(new MessageEvent('message', { data: JSON.stringify({ value: 'test' }) }));
    });

    expect(result.current.data).toEqual({ value: 'test' });
    expect(result.current.lastUpdate).not.toBeNull();
  });

  it('should update data on alert event', () => {
    const { es } = installEventSource();

    const { result } = renderHook(() => useRealtimeData<{ alert: string }>('/api/sse'));

    act(() => {
      es.onopen?.(new Event('open'));
    });

    act(() => {
      es.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify({ type: 'alert', alert: 'test' }) })
      );
    });

    expect(result.current.data).toEqual({ type: 'alert', alert: 'test' });
  });

  it('should call custom onEvent callback', () => {
    const onEvent = jest.fn();
    const { es } = installEventSource();

    renderHook(() => useRealtimeData<string>('/api/sse', { onEvent }));

    act(() => {
      es.onopen?.(new Event('open'));
    });

    act(() => {
      es.onmessage?.(new MessageEvent('message', { data: 'test' }));
    });

    expect(onEvent).toHaveBeenCalled();
  });
});
