import '@testing-library/jest-dom'
import { toHaveNoViolations } from 'jest-axe'

// Add jest-axe custom matcher
expect.extend(toHaveNoViolations)

// Mock Next.js router. `useRouter` is a jest.fn so individual suites can call
// `jest.requireMock('next/navigation').useRouter.mockReturnValue(...)`; the
// default implementation is re-applied below because suites may override it.
const mockRouterFactory = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
  pathname: '/',
  query: {},
  asPath: '/',
})

jest.mock('next/navigation', () => ({
  __sharedNavMock: true,
  useRouter: jest.fn(() => mockRouterFactory()),
  usePathname: jest.fn(() => '/'),
  useSearchParams: jest.fn(() => new URLSearchParams()),
}))

// Mock WebSocket
jest.mock('react-use-websocket', () => ({
  __esModule: true,
  default: () => ({
    sendMessage: jest.fn(),
    lastMessage: null,
    // 1 === WebSocket.OPEN; avoid touching the (absent) WebSocket global so the
    // setup also works in the node test environment.
    readyState: 1,
    getWebSocket: jest.fn(() => ({
      close: jest.fn(),
    })),
  }),
}))

// Mock Socket.io
jest.mock('socket.io-client', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    on: jest.fn(),
    emit: jest.fn(),
    disconnect: jest.fn(),
    connect: jest.fn(),
  })),
}))

// (React Query is intentionally NOT mocked globally: components must use the
// real library so loading/data states behave as they do in production. Suites
// that need to control the client render inside a real QueryClientProvider.)

// The DOM-specific shims below are skipped in the `node` test environment
// (used by tests for server-side code such as lib/serverProxy.ts).
const hasDom = typeof window !== 'undefined'

if (hasDom) {
beforeEach(() => {
  window.matchMedia.mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }))
})

// Mock window.matchMedia. `resetMocks: true` clears the implementation of this
// `jest.fn()` before every test, which made `window.matchMedia(...)` return
// `undefined`; the implementation is therefore re-applied in the beforeEach
// hook below (test files that define their own mock still win, because their
// beforeEach hooks run after this one).
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn(),
})
}

// EventSource is not implemented by jsdom. Provide a minimal, well-behaved
// stand-in so SSE-consuming hooks can be exercised.
if (typeof global.EventSource === 'undefined') {
  class EventSourceStub {
    constructor(url) {
      this.url = url
      this.readyState = EventSourceStub.CONNECTING
      this.onopen = null
      this.onmessage = null
      this.onerror = null
    }
    addEventListener() {}
    removeEventListener() {}
    close() {
      this.readyState = EventSourceStub.CLOSED
    }
  }
  // Spec readyState constants — without these a hook comparing against
  // `EventSource.OPEN`/`.CLOSED` silently misbehaves.
  EventSourceStub.CONNECTING = 0
  EventSourceStub.OPEN = 1
  EventSourceStub.CLOSED = 2
  global.EventSource = EventSourceStub
}

// Re-apply the default router implementation before every test (suites that
// override it in their own beforeEach still win, as those hooks run later).
beforeEach(() => {
  const nav = require('next/navigation')
  if (!nav.__sharedNavMock) return
  nav.useRouter.mockImplementation(() => mockRouterFactory())
  nav.usePathname.mockImplementation(() => '/')
  nav.useSearchParams.mockImplementation(() => new URLSearchParams())
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() { }
  disconnect() { }
  observe() { }
  takeRecords() {
    return []
  }
  unobserve() { }
}

// Radix UI primitives (Select, Slider, Tabs…) rely on these browser APIs, which
// jsdom does not implement. Provide minimal, inert stand-ins.
if (hasDom) {
  if (typeof global.ResizeObserver === 'undefined') {
    global.ResizeObserver = class ResizeObserver {
      observe() { }
      unobserve() { }
      disconnect() { }
    }
  }
  // Pointer capture APIs used by Radix Select's trigger/typeahead.
  if (typeof Element.prototype.hasPointerCapture === 'undefined') {
    Element.prototype.hasPointerCapture = () => false
  }
  if (typeof Element.prototype.setPointerCapture === 'undefined') {
    Element.prototype.setPointerCapture = () => { }
  }
  if (typeof Element.prototype.releasePointerCapture === 'undefined') {
    Element.prototype.releasePointerCapture = () => { }
  }
}

// jsdom does not implement the canvas 2D API, so `getContext('2d')` returns null
// and every chart's drawing code is skipped. Provide an inert, per-canvas cached
// 2D context (all methods are jest.fn spies) so the drawing paths execute and the
// calls can be asserted in tests.
if (hasDom && typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = jest.fn(function (type) {
    if (type !== '2d') return null
    if (!this.__ctx2d) {
      const store = { canvas: this }
      this.__ctx2d = new Proxy(store, {
        get(target, prop) {
          if (prop in target) return target[prop]
          const fn = jest.fn()
          target[prop] = fn
          return fn
        },
        set(target, prop, value) {
          target[prop] = value
          return true
        },
      })
    }
    return this.__ctx2d
  })
}

// Suppress console errors in tests
global.console = {
  ...console,
  error: jest.fn(),
  warn: jest.fn(),
}

// Mock scrollIntoView
if (hasDom) {
  Element.prototype.scrollIntoView = jest.fn()
}

