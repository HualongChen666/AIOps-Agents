import { setRateLimit, acquireToken, withRateLimit } from '@/lib/rateLimiter';

describe('lib/rateLimiter', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  describe('acquireToken', () => {
    it('resolves immediately while tokens remain in the bucket', async () => {
      setRateLimit('unit-fresh', 5, 1000);
      await expect(acquireToken('unit-fresh')).resolves.toBeUndefined();
    });

    it('blocks when the bucket is exhausted and resolves after a refill window', async () => {
      jest.useFakeTimers();
      setRateLimit('unit-block', 1, 1000);

      // Consume the only token synchronously.
      await acquireToken('unit-block');

      let resolved = false;
      const pending = acquireToken('unit-block').then(() => {
        resolved = true;
      });
      await Promise.resolve();
      expect(resolved).toBe(false);

      // Advance past the refill interval and refill via setRateLimit (refilling
      // is the responsibility of setRateLimit in this implementation).
      jest.advanceTimersByTime(1000);
      setRateLimit('unit-block', 1, 1000);
      await jest.advanceTimersByTimeAsync(60);
      await pending;

      expect(resolved).toBe(true);
    });
  });

  describe('withRateLimit', () => {
    it('runs the wrapped function and returns its resolved value', async () => {
      const fn = jest.fn(async () => 'result-ok');
      await expect(withRateLimit('unit-wrap', fn, 10, 1000)).resolves.toBe('result-ok');
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('propagates a rejection from the wrapped function', async () => {
      const fn = jest.fn(async () => {
        throw new Error('downstream failure');
      });
      await expect(withRateLimit('unit-wrap-reject', fn, 10, 1000)).rejects.toThrow(
        'downstream failure'
      );
    });

    it('allows up to maxRequests calls within a window', async () => {
      const fn = jest.fn(async (n: number) => n);
      for (let i = 0; i < 3; i++) {
        await expect(withRateLimit('unit-multi', () => fn(i), 3, 1000)).resolves.toBe(i);
      }
      expect(fn).toHaveBeenCalledTimes(3);
    });
  });

  describe('setRateLimit', () => {
    it('refills tokens based on elapsed time (capped at maxRequests)', async () => {
      jest.useFakeTimers();
      setRateLimit('unit-refill', 2, 1000);
      // Drain both tokens.
      await acquireToken('unit-refill');
      await acquireToken('unit-refill');

      jest.advanceTimersByTime(5000);
      // Elapsed far exceeds the window; refill is capped at maxRequests (2).
      setRateLimit('unit-refill', 2, 1000);

      await expect(acquireToken('unit-refill')).resolves.toBeUndefined();
      await expect(acquireToken('unit-refill')).resolves.toBeUndefined();
    });
  });
});
