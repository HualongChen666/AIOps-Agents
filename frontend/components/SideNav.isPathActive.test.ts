import { describe, it, expect } from 'vitest';
import { isPathActive } from './SideNav';

describe('isPathActive', () => {
  const cases: Array<[string, string, boolean]> = [
    ['/', '/', true],
    ['/alerts', '/alerts', true],
    ['/alerts/123', '/alerts', true],
    ['/alerts/123', '/alerts/123', true],
    ['/alert', '/alerts', false],
    ['/alerts', '/', false],
    ['/alerts/details', '/alerts/details', true],
    ['/alerts/details/456', '/alerts/details', true],
    ['/other', '/alerts', false],
    ['/alerts-and-more', '/alerts', false], // ensure no partial false positive
  ];

  cases.forEach(([cur, href, expected]) => {
    it(`current=${cur} href=${href} => ${expected}`, () => {
      expect(isPathActive(cur, href)).toBe(expected);
    });
  });
});
