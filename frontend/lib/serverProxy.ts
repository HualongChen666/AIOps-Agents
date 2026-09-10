import { NextRequest, NextResponse } from 'next/server';

/**
 * Server-side proxy used by browser pages that must reach backend endpoints
 * protected by `X-Internal-Key`.
 *
 * The key is read from the *server* environment (`INTERNAL_API_KEY`) and is
 * never exposed to the browser or bundled into client JavaScript. Incoming
 * cookies (including the HttpOnly session cookie) are forwarded unchanged so
 * the backend can authorise the end user as well.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

// Headers that must not be copied between the two hops.
const HOP_BY_HOP = new Set([
  'host',
  'connection',
  'content-length',
  'accept-encoding',
  'keep-alive',
  'transfer-encoding',
  'upgrade',
  'te',
  'trailer',
]);

export async function proxyToBackend(
  request: NextRequest,
  backendPath: string,
  options: { internalKey?: boolean } = {}
): Promise<NextResponse> {
  const target = new URL(backendPath, BACKEND_URL);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });

  if (options.internalKey) {
    const internalKey = process.env.INTERNAL_API_KEY;
    if (internalKey) {
      headers.set('X-Internal-Key', internalKey);
    }
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: 'manual',
  };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(target, init);

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === 'set-cookie' || HOP_BY_HOP.has(lower)) return;
    responseHeaders.set(key, value);
  });

  // Forward every Set-Cookie (e.g. the HttpOnly session cookie) verbatim.
  const setCookies =
    typeof upstream.headers.getSetCookie === 'function'
      ? upstream.headers.getSetCookie()
      : [];
  for (const cookie of setCookies) {
    responseHeaders.append('set-cookie', cookie);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
