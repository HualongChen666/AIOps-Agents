import path from 'path';
import fs from 'fs';

const coverageModules = require('@/test-coverage-modules');
const batched = require('@/scripts/run-coverage-batched');

const root = path.resolve(__dirname, '../..');

describe('medium-ledger batch14 — coverage tooling defects', () => {
  describe('FE-012 test-coverage-modules.js', () => {
    it('pads the whole "<seconds>s" token instead of just the "s"', () => {
      const out = coverageModules.formatDuration(12.345);
      expect(out).toBe('12.35s    ');
      expect(out.length).toBe(10);
      // the old expression leaked `undefined` for a missing duration
      expect(coverageModules.formatDuration(undefined).trim()).toBe('0.00s');
    });

    it('skips modules whose test directory does not exist', () => {
      const active = coverageModules.activeModules(coverageModules.TEST_MODULES).map(
        (m: { name: string }) => m.name
      );
      expect(active).toContain('pages');
      // `__tests__/components/layout` is absent; a hard jest run on it would
      // abort the whole batch with "No tests found".
      expect(active).not.toContain('components-layout');
      expect(coverageModules.moduleDir('__tests__/pages/**/*.test.tsx')).toBe('__tests__/pages');
    });
  });

  describe('FE-095 scripts/run-coverage-batched.js', () => {
    it('derives thresholds from the jest config shape', () => {
      expect(
        batched.extractThresholds({ coverageThreshold: { global: { lines: 96, statements: 95 } } })
      ).toEqual({ lines: 96, statements: 95 });
      expect(batched.extractThresholds({})).toBeNull();
    });

    it('sources thresholds from jest.config.js and dropped the stale 43/43/48/50 copy', () => {
      const script = fs.readFileSync(path.join(root, 'scripts/run-coverage-batched.js'), 'utf8');
      expect(script).toContain('jest.config.js');
      // the old hard-coded block must be gone
      expect(script).not.toMatch(/thresholds\s*=\s*\{[^}]*43/);

      // the referenced jest.config.js really does carry the 96/95/95/89 gate
      const jestConfig = fs.readFileSync(path.join(root, 'jest.config.js'), 'utf8');
      expect(jestConfig).toMatch(/lines:\s*96/);
      expect(jestConfig).toMatch(/branches:\s*89/);
    });
  });

  describe('FE-193 app/alerts/datadog — dialog uses DialogTitle, not a raw <title>', () => {
    it('does not nest a native <title> inside DialogHeader', () => {
      const src = fs.readFileSync(path.join(root, 'app/alerts/datadog/page.tsx'), 'utf8');
      expect(src).toContain('<DialogTitle>Datadog配置</DialogTitle>');
      expect(src).not.toContain('<title>Datadog配置</title>');
    });
  });
});
