import {
  CACHE_CONFIG,
  getCacheHeaders,
  SW_CACHE_STRATEGY,
  generateCacheKey,
} from '@/lib/cache-strategy';

describe('lib/cache-strategy', () => {
  describe('CACHE_CONFIG', () => {
    it('defines the expected max ages for each tier', () => {
      expect(CACHE_CONFIG.STATIC.maxAge).toBe(60 * 60 * 1000);
      expect(CACHE_CONFIG.DYNAMIC.maxAge).toBe(5 * 60 * 1000);
      expect(CACHE_CONFIG.REALTIME.maxAge).toBe(30 * 1000);
      expect(CACHE_CONFIG.USER.maxAge).toBe(15 * 60 * 1000);
    });

    it('defines a stale-while-revalidate window for each tier', () => {
      for (const tier of Object.values(CACHE_CONFIG)) {
        expect(tier.staleWhileRevalidate).toBeGreaterThan(0);
        expect(tier.staleWhileRevalidate).toBeLessThanOrEqual(tier.maxAge);
      }
    });
  });

  describe('getCacheHeaders', () => {
    it('converts milliseconds to seconds for STATIC', () => {
      expect(getCacheHeaders('STATIC')).toEqual({
        'Cache-Control': 'max-age=3600, stale-while-revalidate=300',
        'CDN-Cache-Control': 'max-age=3600',
      });
    });

    it('converts milliseconds to seconds for REALTIME', () => {
      expect(getCacheHeaders('REALTIME')).toEqual({
        'Cache-Control': 'max-age=30, stale-while-revalidate=10',
        'CDN-Cache-Control': 'max-age=30',
      });
    });

    it('produces string values', () => {
      const headers = getCacheHeaders('USER');
      expect(typeof headers['Cache-Control']).toBe('string');
      expect(headers['Cache-Control']).toContain('max-age=900');
    });
  });

  describe('SW_CACHE_STRATEGY', () => {
    it('exposes the standard strategy names', () => {
      expect(SW_CACHE_STRATEGY).toEqual({
        CACHE_FIRST: 'cache-first',
        NETWORK_FIRST: 'network-first',
        STALE_WHILE_REVALIDATE: 'stale-while-revalidate',
        CACHE_ONLY: 'cache-only',
        NETWORK_ONLY: 'network-only',
      });
    });
  });

  describe('generateCacheKey', () => {
    it('serializes params in a deterministic (sorted) order', () => {
      const a = generateCacheKey('/api/items', { b: 2, a: 1, c: 3 });
      const b = generateCacheKey('/api/items', { c: 3, a: 1, b: 2 });
      expect(a).toBe('/api/items?a=1&b=2&c=3');
      expect(a).toBe(b);
    });

    it('handles an empty params object', () => {
      expect(generateCacheKey('/api/items', {})).toBe('/api/items?');
    });

    it('stringifies non-string values', () => {
      expect(generateCacheKey('k', { page: 2, active: true })).toBe('k?active=true&page=2');
    });
  });
});
