import { NextRequest } from 'next/server';
import { proxyToBackend } from '@/lib/serverProxy';

/**
 * Server-side proxy for `/api/guard/*`.
 *
 * Several guard endpoints (audit/stats) require `X-Internal-Key`. The browser
 * no longer holds that key, so these calls are relayed through the Next.js
 * server, which injects it from the server-only `INTERNAL_API_KEY` env var.
 * This route handler takes precedence over the generic `/api/:path*` rewrite.
 */

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function backendPath(request: NextRequest): string {
  const segments = request.nextUrl.pathname.replace(/^\/api\/guard\/?/, '');
  return `/api/guard/${segments}`;
}

async function handle(request: NextRequest) {
  return proxyToBackend(request, backendPath(request), { internalKey: true });
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
