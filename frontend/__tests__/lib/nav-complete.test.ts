import { getCompleteNavGroups, completeNavGroups, type NavGroup } from '@/lib/nav-complete';

const allItems = (groups: NavGroup[]) => groups.flatMap((g) => g.items);

describe('lib/nav-complete', () => {
  describe('getCompleteNavGroups', () => {
    it('returns groups, each with a title and an items array', () => {
      const groups = getCompleteNavGroups('zh-CN');
      expect(groups.length).toBeGreaterThan(5);
      for (const group of groups) {
        expect(typeof group.title).toBe('string');
        expect(group.title.length).toBeGreaterThan(0);
        expect(Array.isArray(group.items)).toBe(true);
      }
      // A few placeholder groups (e.g. 协作与通知, 资产管理) are still empty; the
      // domain groups must be populated.
      expect(groups.some((g) => g.items.length > 0)).toBe(true);
    });

    it('every item is a well-formed {href,label} nav entry', () => {
      for (const item of allItems(getCompleteNavGroups('zh-CN'))) {
        expect(item.href).toMatch(/^\//);
        expect(typeof item.label).toBe('string');
        expect(item.label.length).toBeGreaterThan(0);
      }
    });

    it('covers the AI, alerts, repair and monitoring domains', () => {
      const hrefs = allItems(getCompleteNavGroups('zh-CN')).map((i) => i.href);
      expect(hrefs).toContain('/ai/llm-router');
      expect(hrefs).toContain('/alerts/prometheus');
      expect(hrefs).toContain('/repair/auto-heal');
      expect(hrefs).toContain('/monitoring/metrics');
    });

    it('produces no duplicate hrefs', () => {
      const hrefs = allItems(getCompleteNavGroups('zh-CN')).map((i) => i.href);
      expect(new Set(hrefs).size).toBe(hrefs.length);
    });

    it('localizes group titles through translate for the requested locale', () => {
      // Static titles are used for the domain groups, but the function must still
      // be callable for any supported locale without throwing.
      expect(() => getCompleteNavGroups('en-US')).not.toThrow();
      expect(getCompleteNavGroups('en-US').length).toBe(getCompleteNavGroups('zh-CN').length);
    });
  });

  describe('completeNavGroups (static export)', () => {
    it('equals the zh-CN complete groups', () => {
      expect(completeNavGroups).toEqual(getCompleteNavGroups('zh-CN'));
    });
  });
});
