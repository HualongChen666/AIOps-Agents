import { toast } from 'react-hot-toast';
import WebSocketClient from '@/lib/websocket';

jest.mock('react-hot-toast', () => ({ toast: { error: jest.fn() } }));

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];
  static throwOnConstruct = false;

  url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  send = jest.fn();
  close = jest.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  constructor(url: string) {
    if (MockWebSocket.throwOnConstruct) {
      throw new Error('construct failed');
    }
    this.url = url;
    MockWebSocket.instances.push(this);
  }
}

const NativeWebSocket = global.WebSocket;

beforeAll(() => {
  (global as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
});

afterAll(() => {
  (global as unknown as { WebSocket: unknown }).WebSocket = NativeWebSocket;
});

describe('lib/websocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    MockWebSocket.throwOnConstruct = false;
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('connect', () => {
    it('opens a socket to the configured URL', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.instances[0].url).toBe('wss://example.test/ws');
    });

    it('resets the reconnect counter on open', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      expect(() => MockWebSocket.instances[0].onopen?.()).not.toThrow();
    });

    it('reports an error and notifies the user on socket error', async () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      MockWebSocket.instances[0].onerror?.(new Error('x'));
      await Promise.resolve();
      await Promise.resolve();
      expect(toast.error).toHaveBeenCalledWith('WebSocket 连接失败，实时功能可能不可用');
    });
  });

  describe('onMessage', () => {
    it('parses a JSON payload and forwards it to the callback', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      const cb = jest.fn();
      client.onMessage(cb);
      MockWebSocket.instances[0].onmessage?.({ data: JSON.stringify({ type: 'ping' }) });
      expect(cb).toHaveBeenCalledWith({ type: 'ping' });
    });

    it('ignores malformed JSON without calling the callback', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      const cb = jest.fn();
      client.onMessage(cb);
      MockWebSocket.instances[0].onmessage?.({ data: 'not-json' });
      expect(cb).not.toHaveBeenCalled();
      expect(console.error).toHaveBeenCalled();
    });

    it('is a no-op when called before connect', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      expect(() => client.onMessage(jest.fn())).not.toThrow();
    });
  });

  describe('send', () => {
    it('sends a JSON string when the socket is open', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      const ws = MockWebSocket.instances[0];
      ws.readyState = MockWebSocket.OPEN;
      client.send({ action: 'subscribe', topic: 'alerts' });
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'subscribe', topic: 'alerts' }));
    });

    it('warns instead of sending when the socket is not open', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      MockWebSocket.instances[0].readyState = MockWebSocket.CONNECTING;
      client.send({ a: 1 });
      expect(MockWebSocket.instances[0].send).not.toHaveBeenCalled();
      expect(console.warn).toHaveBeenCalledWith('WebSocket is not connected');
    });
  });

  describe('getReadyState / disconnect', () => {
    it('reports CLOSED before connect', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      expect(client.getReadyState()).toBe(MockWebSocket.CLOSED);
    });

    it('reflects the underlying readyState after connect', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      MockWebSocket.instances[0].readyState = MockWebSocket.OPEN;
      expect(client.getReadyState()).toBe(MockWebSocket.OPEN);
    });

    it('closes the socket and clears it on disconnect', () => {
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      const ws = MockWebSocket.instances[0];
      client.disconnect();
      expect(ws.close).toHaveBeenCalled();
      expect(client.getReadyState()).toBe(MockWebSocket.CLOSED);
    });
  });

  describe('reconnection', () => {
    it('schedules a reconnect after the socket closes', () => {
      jest.useFakeTimers();
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      expect(MockWebSocket.instances).toHaveLength(1);

      MockWebSocket.instances[0].onclose?.();

      jest.advanceTimersByTime(1000);
      expect(MockWebSocket.instances).toHaveLength(2);
      jest.useRealTimers();
    });

    it('gives up after the maximum number of attempts', () => {
      jest.useFakeTimers();
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();

      // Drive 6 close events, letting each scheduled reconnect fire in between.
      for (let i = 0; i < 6; i++) {
        MockWebSocket.instances[MockWebSocket.instances.length - 1].onclose?.();
        jest.advanceTimersByTime(60000);
      }

      expect(console.error).toHaveBeenCalledWith('Max reconnection attempts reached');
      jest.useRealTimers();
    });

    it('schedules a reconnect when the constructor throws', () => {
      jest.useFakeTimers();
      const client = new WebSocketClient('wss://example.test/ws');
      MockWebSocket.throwOnConstruct = true;
      client.connect(); // throws internally, should schedule a reconnect
      MockWebSocket.throwOnConstruct = false;
      jest.advanceTimersByTime(1000);
      expect(MockWebSocket.instances).toHaveLength(1);
      jest.useRealTimers();
    });
  });
});
