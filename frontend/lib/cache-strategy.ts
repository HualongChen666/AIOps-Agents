/**
 * Cache Strategy Utilities
 * 
 * Provides utilities for cache configuration and management
 * to improve application performance.
 */

/**
 * Cache configuration for different data types
 */
export const CACHE_CONFIG = {
  // Static data - cache for 1 hour
  STATIC: {
    maxAge: 60 * 60 * 1000, // 1 hour
    staleWhileRevalidate: 5 * 60 * 1000, // 5 minutes
  },
  // Dynamic data - cache for 5 minutes
  DYNAMIC: {
    maxAge: 5 * 60 * 1000, // 5 minutes
    staleWhileRevalidate: 60 * 1000, // 1 minute
  },
  // Real-time data - cache for 30 seconds
  REALTIME: {
    maxAge: 30 * 1000, // 30 seconds
    staleWhileRevalidate: 10 * 1000, // 10 seconds
  },
  // User data - cache for 15 minutes
  USER: {
    maxAge: 15 * 60 * 1000, // 15 minutes
    staleWhileRevalidate: 2 * 60 * 1000, // 2 minutes
  },
};

/**
 * Get cache headers for API responses
 */
export function getCacheHeaders(type: keyof typeof CACHE_CONFIG): Record<string, string> {
  const config = CACHE_CONFIG[type];
  return {
    'Cache-Control': `max-age=${config.maxAge / 1000}, stale-while-revalidate=${config.staleWhileRevalidate / 1000}`,
    'CDN-Cache-Control': `max-age=${config.maxAge / 1000}`,
  };
}

/**
 * Service Worker cache strategy
 */
export const SW_CACHE_STRATEGY = {
  // Cache first, then network
  CACHE_FIRST: 'cache-first',
  // Network first, then cache
  NETWORK_FIRST: 'network-first',
  // Stale while revalidate
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate',
  // Cache only
  CACHE_ONLY: 'cache-only',
  // Network only
  NETWORK_ONLY: 'network-only',
};

/**
 * Cache key generator
 */
export function generateCacheKey(prefix: string, params: Record<string, any>): string {
  const sortedParams = Object.keys(params)
    .sort()
    .map((key) => `${key}=${params[key]}`)
    .join('&');
  return `${prefix}?${sortedParams}`;
}