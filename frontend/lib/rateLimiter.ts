// Simple in-memory rate limiter for frontend API calls
// Implements token bucket per endpoint (identified by method+url)
// maxRequests: max number of requests allowed in intervalMs
// intervalMs: time window in milliseconds

interface Bucket {
  tokens: number;
  lastRefill: number;
}

const buckets: Record<string, Bucket> = {};

// Defaults used when `acquireToken` is called for a key that was never
// configured through `setRateLimit`. Without this an unconfigured key has no
// bucket, so the retry loop below would spin forever and the returned promise
// would never settle.
const DEFAULT_MAX_REQUESTS = 10;
const DEFAULT_INTERVAL_MS = 1000;

export function setRateLimit(
  key: string,
  maxRequests: number = 10,
  intervalMs: number = 1000
) {
  const now = Date.now();
  const bucket = buckets[key] || { tokens: maxRequests, lastRefill: now };
  const elapsed = now - bucket.lastRefill;
  const refillTokens = Math.floor((elapsed / intervalMs) * maxRequests);
  if (refillTokens > 0) {
    bucket.tokens = Math.min(maxRequests, bucket.tokens + refillTokens);
    bucket.lastRefill = now;
  }
  buckets[key] = bucket;
}

export function acquireToken(key: string): Promise<void> {
  return new Promise((resolve) => {
    const attempt = () => {
      let bucket = buckets[key];
      if (!bucket) {
        // Lazily initialise the bucket with the default limit so that a
        // standalone `acquireToken` (without a prior `setRateLimit`) still
        // resolves instead of hanging on a bucket that never appears.
        setRateLimit(key, DEFAULT_MAX_REQUESTS, DEFAULT_INTERVAL_MS);
        bucket = buckets[key];
      }
      if (bucket.tokens > 0) {
        bucket.tokens -= 1;
        resolve();
      } else {
        // wait a short time before retry
        setTimeout(attempt, 50);
      }
    };
    attempt();
  });
}

// Helper to wrap an axios request with rate limiting
export async function withRateLimit<T>(
  key: string,
  fn: () => Promise<T>,
  maxRequests: number = 10,
  intervalMs: number = 1000
): Promise<T> {
  setRateLimit(key, maxRequests, intervalMs);
  await acquireToken(key);
  return fn();
}
