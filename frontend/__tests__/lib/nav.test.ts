import { getNavGroups, navGroups, getCompleteNavGroups, type NavGroup } from '@/lib/nav';

const hrefs = (groups: NavGroup[]) => groups.flatMap((g) => g.items.map((i) => i.href));

describe('lib/nav', () => {
  describe('getNavGroups', () => {
    it('returns a non-empty list of groups with translated titles and items', () => {
      const groups = getNavGroups('zh-CN');
      expect(groups.length).toBeGreaterThan(0);
      for (const group of groups) {
        expect(typeof group.title).toBe('string');
        expect(group.title.length).toBeGreaterThan(0);
        expect(Array.isArray(group.items)).toBe(true);
        expect(group.items.length).toBeGreaterThan(0);
        for (const item of group.items) {
          expect(item.href).toMatch(/^\//);
          expect(typeof item.label).toBe('string');
        }
      }
    });

    it('includes the core navigation targets', () => {
      const all = hrefs(getNavGroups('zh-CN'));
      expect(all).toContain('/');
      expect(all).toContain('/dashboard');
      expect(all).toContain('/alerts');
      expect(all).toContain('/topology');
      expect(all).toContain('/settings');
      expect(all).toContain('/all-features');
    });

    it('localizes labels for zh-CN and en-US', () => {
      const zh = getNavGroups('zh-CN').flatMap((g) => g.items);
      const en = getNavGroups('en-US').flatMap((g) => g.items);
      const zhHome = zh.find((i) => i.href === '/');
      const enHome = en.find((i) => i.href === '/');
      expect(zhHome?.label).toBe('首页');
      expect(enHome?.label).toBe('Home');
    });

    it('opens the API docs item in a new tab', () => {
      const item = getNavGroups('zh-CN').flatMap((g) => g.items).find((i) => i.href === '/api-documentation');
      expect(item?.target).toBe('_blank');
    });
  });

  describe('navGroups (static export)', () => {
    it('equals the zh-CN groups', () => {
      expect(navGroups).toEqual(getNavGroups('zh-CN'));
    });
  });

  describe('getCompleteNavGroups re-export', () => {
    it('is exported and returns a larger set than the curated nav', () => {
      const complete = getCompleteNavGroups('zh-CN');
      expect(complete.length).toBeGreaterThan(getNavGroups('zh-CN').length);
      expect(hrefs(complete)).toContain('/ai/llm-router');
    });
  });
});
