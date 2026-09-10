/**
 * @jest-environment node
 *
 * The proxy uses the Web Fetch API (Request/Response/Headers), which the jsdom
 * environment does not provide. Node 18+ exposes them natively.
 */
import { proxyToBackend } from '@/lib/serverProxy';
import { NextResponse } from 'next/server';

function makeRequest(
  url: string,
  init: { method?: string; headers?: Record<string, string>; body?: string } = {}
): any {
  const parsed = new URL(url);
  return {
    method: init.method || 'GET',
    headers: new Headers(init.headers || {}),
    nextUrl: parsed,
    arrayBuffer: async () => new TextEncoder().encode(init.body || '').buffer,
  };
}

describe('serverProxy', () => {
  const originalFetch = global.fetch;
  const originalKey = process.env.INTERNAL_API_KEY;

  beforeEach(() => {
    process.env.INTERNAL_API_KEY = 'server-side-secret';
  });

  afterEach(() => {
    global.fetch = originalFetch;
    if (originalKey === undefined) delete process.env.INTERNAL_API_KEY;
    else process.env.INTERNAL_API_KEY = originalKey;
    jest.restoreAllMocks();
  });

  it('injects the internal key server-side for protected endpoints', async () => {
    const fetchMock = jest.fn(async () => new Response('{"ok":true}', { status: 200 }));
    global.fetch = fetchMock as any;

    const request = makeRequest('http://localhost:3000/api/v1/approvals/pending');
    await proxyToBackend(request, '/api/v1/approvals/pending', { internalKey: true });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [target, init] = fetchMock.mock.calls[0] as any;
    expect(String(target)).toBe('http://127.0.0.1:8000/api/v1/approvals/pending');
    expect(new Headers(init.headers).get('X-Internal-Key')).toBe('server-side-secret');
  });

  it('does not inject the internal key when not requested', async () => {
    const fetchMock = jest.fn(async () => new Response('{}', { status: 200 }));
    global.fetch = fetchMock as any;

    const request = makeRequest('http://localhost:3000/api/guard/check');
    await proxyToBackend(request, '/api/guard/check');

    const [, init] = fetchMock.mock.calls[0] as any;
    expect(new Headers(init.headers).get('X-Internal-Key')).toBeNull();
  });

  it('forwards the incoming session cookie to the backend', async () => {
    const fetchMock = jest.fn(async () => new Response('{}', { status: 200 }));
    global.fetch = fetchMock as any;

    const request = makeRequest('http://localhost:3000/api/guard/audit', {
      headers: { cookie: 'access_token=abc.def.ghi' },
    });
    await proxyToBackend(request, '/api/guard/audit', { internalKey: true });

    const [, init] = fetchMock.mock.calls[0] as any;
    expect(new Headers(init.headers).get('cookie')).toBe('access_token=abc.def.ghi');
  });

  it('preserves query strings and upstream status', async () => {
    const fetchMock = jest.fn(async () => new Response('nope', { status: 403 }));
    global.fetch = fetchMock as any;

    const request = makeRequest('http://localhost:3000/api/guard/audit?limit=50');
    const response = await proxyToBackend(request, '/api/guard/audit', { internalKey: true });

    const [target] = fetchMock.mock.calls[0] as any;
    expect(String(target)).toBe('http://127.0.0.1:8000/api/guard/audit?limit=50');
    expect(response).toBeInstanceOf(NextResponse);
    expect(response.status).toBe(403);
  });

  it('forwards Set-Cookie headers from the backend verbatim', async () => {
    const upstream = new Response('{}', { status: 200 });
    upstream.headers.append(
      'set-cookie',
      'access_token=xyz; HttpOnly; Path=/; SameSite=lax'
    );
    global.fetch = jest.fn(async () => upstream) as any;

    const request = makeRequest('http://localhost:3000/api/v1/approvals/pending');
    const response = await proxyToBackend(request, '/api/v1/approvals/pending', {
      internalKey: true,
    });

    expect(response.headers.get('set-cookie')).toContain('HttpOnly');
  });

  it('sends a body for non-GET requests', async () => {
    const fetchMock = jest.fn(async () => new Response('{}', { status: 200 }));
    global.fetch = fetchMock as any;

    const request = makeRequest('http://localhost:3000/api/v1/approvals/reject', {
      method: 'POST',
      body: '{"alert_id":"a1"}',
    });
    await proxyToBackend(request, '/api/v1/approvals/reject', { internalKey: true });

    const [, init] = fetchMock.mock.calls[0] as any;
    expect(init.method).toBe('POST');
    expect(Buffer.from(init.body).toString()).toBe('{"alert_id":"a1"}');
  });
});
