import { toast } from 'react-hot-toast';
import { keyboardNavigation } from '@/lib/accessibility';
import { acquireToken } from '@/lib/rateLimiter';
import WebSocketClient from '@/lib/websocket';

jest.mock('react-hot-toast', () => ({ toast: { error: jest.fn() } }));

describe('medium-ledger batch12 — lib defects', () => {
  describe('FE-018 lib/accessibility.getShortcutHint', () => {
    afterEach(() => {
      Object.defineProperty(navigator, 'platform', { value: 'Win32', configurable: true });
    });

    it('does not throw (and defaults to Ctrl) when navigator.platform is unavailable', () => {
      // Reproduces the SSR/reference-error path: platform undefined previously
      // made `navigator.platform.toLowerCase()` throw.
      Object.defineProperty(navigator, 'platform', { value: undefined, configurable: true });
      expect(() => keyboardNavigation.getShortcutHint(['K'])).not.toThrow();
      expect(keyboardNavigation.getShortcutHint(['K'])).toBe('Ctrl+K');
    });
  });

  describe('FE-028 lib/rateLimiter.acquireToken', () => {
    it('resolves for a key that was never configured instead of polling forever', async () => {
      // Before the fix an unconfigured key had no bucket, so the retry loop
      // never settled and this promise hung until the jest timeout.
      await expect(acquireToken('batch12-unconfigured-key')).resolves.toBeUndefined();
    });
  });

  describe('FE-031 lib/websocket reconnection', () => {
    class MockWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;
      static instances: MockWebSocket[] = [];

      url: string;
      readyState = 0;
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      onmessage: ((e: { data: string }) => void) | null = null;
      send = jest.fn();
      close = jest.fn(() => {
        this.readyState = MockWebSocket.CLOSED;
      });

      constructor(url: string) {
        this.url = url;
        MockWebSocket.instances.push(this);
      }
    }

    const NativeWebSocket = (global as any).WebSocket;

    beforeAll(() => {
      (global as any).WebSocket = MockWebSocket;
    });

    afterAll(() => {
      (global as any).WebSocket = NativeWebSocket;
    });

    beforeEach(() => {
      MockWebSocket.instances = [];
      jest.clearAllMocks();
      jest.useRealTimers();
    });

    it('closes the previous socket before opening the reconnect', () => {
      jest.useFakeTimers();
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      const first = MockWebSocket.instances[0];

      first.onclose?.();
      jest.advanceTimersByTime(1000);

      expect(first.close).toHaveBeenCalled();
      expect(MockWebSocket.instances).toHaveLength(2);
      jest.useRealTimers();
    });

    it('cancels a pending reconnect on an explicit disconnect', () => {
      jest.useFakeTimers();
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      MockWebSocket.instances[0].onclose?.();

      client.disconnect();
      jest.advanceTimersByTime(60000);

      // The queued reconnect must not create a new socket after disconnect.
      expect(MockWebSocket.instances).toHaveLength(1);
      jest.useRealTimers();
    });

    it('notifies the user when the socket closes (unchanged behaviour)', async () => {
      jest.useFakeTimers();
      const client = new WebSocketClient('wss://example.test/ws');
      client.connect();
      MockWebSocket.instances[0].onclose?.();
      await Promise.resolve();
      await Promise.resolve();
      expect(toast.error).toHaveBeenCalledWith('WebSocket 连接断开，正在尝试重连...');
      jest.useRealTimers();
    });
  });
});
