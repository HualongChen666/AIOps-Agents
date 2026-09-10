import {
  hexToRgb,
  rgbToLuminance,
  calculateContrastRatio,
  checkWcagCompliance,
  getContrastingTextColor,
  adjustColorForContrast,
  colorPalette,
  generateAccessibleCombinations,
} from '@/lib/color-contrast';

describe('lib/color-contrast', () => {
  describe('hexToRgb', () => {
    it('parses a 6-digit hex with a leading hash', () => {
      expect(hexToRgb('#ff0000')).toEqual({ r: 255, g: 0, b: 0 });
    });

    it('parses a 6-digit hex without a leading hash', () => {
      expect(hexToRgb('00ff00')).toEqual({ r: 0, g: 255, b: 0 });
    });

    it('parses mixed-case hex', () => {
      expect(hexToRgb('#AbCdEf')).toEqual({ r: 0xab, g: 0xcd, b: 0xef });
    });

    it('falls back to black for invalid input', () => {
      expect(hexToRgb('#xyz')).toEqual({ r: 0, g: 0, b: 0 });
      expect(hexToRgb('')).toEqual({ r: 0, g: 0, b: 0 });
    });
  });

  describe('rgbToLuminance', () => {
    it('returns 0 for black', () => {
      expect(rgbToLuminance(0, 0, 0)).toBeCloseTo(0, 5);
    });

    it('returns 1 for white', () => {
      expect(rgbToLuminance(255, 255, 255)).toBeCloseTo(1, 5);
    });

    it('increases with brightness', () => {
      expect(rgbToLuminance(128, 128, 128)).toBeGreaterThan(rgbToLuminance(64, 64, 64));
    });
  });

  describe('calculateContrastRatio', () => {
    it('returns 21 for black on white', () => {
      expect(calculateContrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 1);
    });

    it('is symmetric', () => {
      expect(calculateContrastRatio('#000000', '#ffffff')).toBeCloseTo(
        calculateContrastRatio('#ffffff', '#000000'),
        10
      );
    });

    it('returns 1 for identical colors', () => {
      expect(calculateContrastRatio('#123456', '#123456')).toBeCloseTo(1, 10);
    });
  });

  describe('checkWcagCompliance', () => {
    it('rates black-on-white as AAA for normal text', () => {
      const r = checkWcagCompliance('#000000', '#ffffff', 'normal');
      expect(r.passesAA).toBe(true);
      expect(r.passesAAA).toBe(true);
      expect(r.level).toBe('AAA');
    });

    it('uses a 3:1 threshold for large text', () => {
      // #767676 on white is ~4.54:1 → fails AAA normal (7) but passes large AA (3).
      const r = checkWcagCompliance('#767676', '#ffffff', 'large');
      expect(r.passesAA).toBe(true);
    });

    it('flags a clear failure', () => {
      const r = checkWcagCompliance('#eeeeee', '#ffffff', 'normal');
      expect(r.passesAA).toBe(false);
      expect(r.passesAAA).toBe(false);
      expect(r.level).toBe('fail');
    });

    it('reports AA (not AAA) for mid-range contrast on normal text', () => {
      const r = checkWcagCompliance('#767676', '#ffffff', 'normal');
      expect(r.level).toBe('AA');
    });
  });

  describe('getContrastingTextColor', () => {
    it('picks the dark color on a light background', () => {
      expect(getContrastingTextColor('#ffffff')).toBe('#000000');
    });

    it('picks the light color on a dark background', () => {
      expect(getContrastingTextColor('#000000')).toBe('#FFFFFF');
    });

    it('honors custom light/dark colors and threshold', () => {
      expect(getContrastingTextColor('#ffffff', { lightColor: '#eee', darkColor: '#111' })).toBe('#111');
      expect(getContrastingTextColor('#808080', { threshold: 0.9 })).toBe('#FFFFFF');
    });
  });

  describe('adjustColorForContrast', () => {
    it('returns the color unchanged when the target ratio is already met', () => {
      expect(adjustColorForContrast('#000000', '#ffffff', 4.5)).toBe('#000000');
    });

    it('returns a valid 7-char hex string', () => {
      const adjusted = adjustColorForContrast('#abcdef', '#ffffff', 4.5);
      expect(adjusted).toMatch(/^#[0-9a-f]{6}$/);
    });

    it('reaches the requested ratio when starting below it', () => {
      // Regression guard for the inverted lighten/darken direction (task #5):
      // '#cccccc' against white must be darkened until the 4.5 ratio is met.
      const adjusted = adjustColorForContrast('#cccccc', '#ffffff', 4.5);
      expect(calculateContrastRatio(adjusted, '#ffffff')).toBeGreaterThanOrEqual(4.5);
    });

    it('lightens a colour that is darker than the target to raise contrast', () => {
      const adjusted = adjustColorForContrast('#333333', '#000000', 4.5);
      expect(calculateContrastRatio(adjusted, '#000000')).toBeGreaterThanOrEqual(4.5);
    });
  });

  describe('colorPalette', () => {
    it('exposes the primary palette', () => {
      expect(colorPalette.primary.blue).toBe('#3B82F6');
      expect(colorPalette.primary.red).toBe('#EF4444');
    });

    it('exposes neutral colors', () => {
      expect(colorPalette.neutral.white).toBe('#FFFFFF');
      expect(colorPalette.neutral.black).toBe('#000000');
    });

    it('getTextColor delegates to getContrastingTextColor', () => {
      expect(colorPalette.getTextColor('#000000')).toBe('#FFFFFF');
    });

    it('checkContrast delegates to checkWcagCompliance', () => {
      expect(colorPalette.checkContrast('#000000', '#ffffff').level).toBe('AAA');
    });
  });

  describe('generateAccessibleCombinations', () => {
    it('produces a full set of accessible colors for a base color', () => {
      const combo = generateAccessibleCombinations('#3B82F6');
      expect(combo.background).toBe('#3B82F6');
      expect(combo.text).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(combo.border).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(combo.hover).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(combo.focus).toMatch(/^#[0-9a-fA-F]{6}$/);
    });

    it('derives a text color that contrasts with the background', () => {
      const combo = generateAccessibleCombinations('#ffffff');
      expect(combo.text).toBe('#000000');
      expect(calculateContrastRatio(combo.text, combo.background)).toBeGreaterThanOrEqual(4.5);
    });
  });
});
