const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  maxWorkers: 1,
  workerIdleMemoryLimit: '512MB',
  transformIgnorePatterns: [
    'node_modules/(?!(msw|@msw-js)/)',
  ],
  cache: false,
  clearMocks: true,
  // NOTE: `resetMocks` must stay false. It calls `.mockReset()` on every mock
  // before each test, which *removes the implementation* of mocks created at
  // module scope (e.g. `jest.fn(() => ({...}))` in a test file) and made those
  // factories return `undefined`. `clearMocks` still isolates call history.
  resetMocks: false,
  restoreMocks: true,
  collectCoverageFrom: [
    'components/**/*.{js,jsx,ts,tsx}',
    'lib/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
    '!**/coverage/**',
    '!**/jest.config.js',
    '!**/jest.setup.js',
    '!**/__tests__/**',
  ],
  // Measured baseline (2026-09-10, after backfilling component/lib tests):
  // lines 97.63% / statements 96.7% / functions 97.18% / branches 90.65% over
  // components/** + lib/** (merged from module batches — see
  // scripts/run-coverage-batched.js + scripts/merge-coverage.js, because this
  // host (~1.4 GB RAM, no swap) OOM-kills a single full-suite run).
  // Thresholds sit ~1.5pt under the measured values so the gate catches real
  // regressions without failing on run-to-run noise. Previously the object
  // enforced 43/43/48/50 (baseline lines 44.6%).
  coverageThreshold: {
    global: {
      lines: 96,
      statements: 95,
      functions: 95,
      branches: 89,
    },
  },
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    // Playwright suites (run via `npm run test:e2e` / `test:visual`).
    '/__tests__/e2e/',
    '/__tests__/visual/',
    '/tests/e2e/',
    // Shared test fixtures/helpers, not test suites themselves.
    '/__tests__/mocks/',
    '/__tests__/setup\\.ts$',
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)