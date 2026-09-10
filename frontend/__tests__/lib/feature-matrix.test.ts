import {
  featureMatrix,
  getFeatureStatus,
  isFeatureAvailable,
  getAvailableFeatures,
  getFeatureStats,
  type FeatureStatus,
} from '@/lib/feature-matrix';

describe('lib/feature-matrix', () => {
  describe('featureMatrix data integrity', () => {
    it('every entry exposes status/api/page and optional table/description', () => {
      for (const [key, info] of Object.entries(featureMatrix)) {
        expect(typeof key).toBe('string');
        expect(['available', 'developing', 'unavailable']).toContain(info.status);
        expect(typeof info.api).toBe('string');
        expect(info.api.length).toBeGreaterThan(0);
        expect(typeof info.page).toBe('string');
        expect(info.page.startsWith('/')).toBe(true);
      }
    });

    it('contains the documented core features', () => {
      expect(featureMatrix.alerts.page).toBe('/alerts');
      expect(featureMatrix.dashboard.api).toBe('/api/v1/metrics/summary');
      expect(featureMatrix.topology.page).toBe('/topology');
      expect(featureMatrix['auto-heal'].status).toBe('available');
    });
  });

  describe('getFeatureStatus', () => {
    it('returns the declared status for a known feature', () => {
      expect(getFeatureStatus('alerts')).toBe<FeatureStatus>('available');
    });

    it('returns "unavailable" for an unknown feature', () => {
      expect(getFeatureStatus('does-not-exist')).toBe('unavailable');
    });
  });

  describe('isFeatureAvailable', () => {
    it('is true for an available feature', () => {
      expect(isFeatureAvailable('dashboard')).toBe(true);
    });

    it('is false for an unknown feature', () => {
      expect(isFeatureAvailable('nope')).toBe(false);
    });
  });

  describe('getAvailableFeatures', () => {
    it('returns only available feature keys and includes known ones', () => {
      const available = getAvailableFeatures();
      expect(available).toContain('alerts');
      expect(available).toContain('ai-llm-router');
      for (const key of available) {
        expect(featureMatrix[key].status).toBe('available');
      }
    });

    it('length matches the number of available entries', () => {
      const expected = Object.values(featureMatrix).filter((i) => i.status === 'available').length;
      expect(getAvailableFeatures()).toHaveLength(expected);
    });
  });

  describe('getFeatureStats', () => {
    it('totals equal the matrix size and per-status counts sum to the total', () => {
      const stats = getFeatureStats();
      expect(stats.total).toBe(Object.keys(featureMatrix).length);
      expect(stats.available + stats.developing + stats.unavailable).toBe(stats.total);
    });

    it('counts every available entry', () => {
      const stats = getFeatureStats();
      expect(stats.available).toBe(getAvailableFeatures().length);
    });
  });
});
