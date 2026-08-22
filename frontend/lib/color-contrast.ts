/**
 * Color Contrast Utilities
 *
 * Provides color contrast checking and optimization utilities
 * for WCAG compliance.
 */

/**
 * Convert hex color to RGB
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : { r: 0, g: 0, b: 0 };
}

/**
 * Convert RGB to luminance
 */
export function rgbToLuminance(r: number, g: number, b: number): number {
  const a = [r, g, b].map((v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
}

/**
 * Calculate contrast ratio between two colors
 */
export function calculateContrastRatio(
  foreground: string,
  background: string
): number {
  const fg = hexToRgb(foreground);
  const bg = hexToRgb(background);

  const lum1 = rgbToLuminance(fg.r, fg.g, fg.b);
  const lum2 = rgbToLuminance(bg.r, bg.g, bg.b);

  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);

  return (brightest + 0.05) / (darkest + 0.05);
}

/**
 * Check if contrast ratio meets WCAG standards
 */
export function checkWcagCompliance(
  foreground: string,
  background: string,
  textSize: 'normal' | 'large' = 'normal'
): {
  ratio: number;
  passesAA: boolean;
  passesAAA: boolean;
  level: 'fail' | 'AA' | 'AAA';
} {
  const ratio = calculateContrastRatio(foreground, background);
  
  const aaThreshold = textSize === 'large' ? 3 : 4.5;
  const aaaThreshold = textSize === 'large' ? 4.5 : 7;

  const passesAA = ratio >= aaThreshold;
  const passesAAA = ratio >= aaaThreshold;

  let level: 'fail' | 'AA' | 'AAA' = 'fail';
  if (passesAAA) level = 'AAA';
  else if (passesAA) level = 'AA';

  return {
    ratio,
    passesAA,
    passesAAA,
    level,
  };
}

/**
 * Get suggested text color for a background
 */
export function getContrastingTextColor(
  backgroundColor: string,
  options: {
    lightColor?: string;
    darkColor?: string;
    threshold?: number;
  } = {}
): string {
  const {
    lightColor = '#FFFFFF',
    darkColor = '#000000',
    threshold = 0.5,
  } = options;

  const bg = hexToRgb(backgroundColor);
  const luminance = rgbToLuminance(bg.r, bg.g, bg.b);

  return luminance > threshold ? darkColor : lightColor;
}

/**
 * Adjust color to meet contrast requirements
 */
export function adjustColorForContrast(
  color: string,
  targetColor: string,
  targetRatio: number = 4.5
): string {
  let currentRatio = calculateContrastRatio(color, targetColor);
  let adjustedColor = color;
  let iterations = 0;
  const maxIterations = 100;

  while (currentRatio < targetRatio && iterations < maxIterations) {
    const rgb = hexToRgb(adjustedColor);
    const targetRgb = hexToRgb(targetColor);
    
    // Move color towards black or white depending on target
    const targetLuminance = rgbToLuminance(targetRgb.r, targetRgb.g, targetRgb.b);
    const currentLuminance = rgbToLuminance(rgb.r, rgb.g, rgb.b);
    
    if (currentLuminance > targetLuminance) {
      // Darken the color
      adjustedColor = darkenColor(adjustedColor, 0.1);
    } else {
      // Lighten the color
      adjustedColor = lightenColor(adjustedColor, 0.1);
    }
    
    currentRatio = calculateContrastRatio(adjustedColor, targetColor);
    iterations++;
  }

  return adjustedColor;
}

/**
 * Darken a color by a percentage
 */
function darkenColor(hex: string, percent: number): string {
  const rgb = hexToRgb(hex);
  const factor = 1 - percent;
  
  const r = Math.round(rgb.r * factor);
  const g = Math.round(rgb.g * factor);
  const b = Math.round(rgb.b * factor);
  
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/**
 * Lighten a color by a percentage
 */
function lightenColor(hex: string, percent: number): string {
  const rgb = hexToRgb(hex);
  const factor = 1 + percent;
  
  const r = Math.min(255, Math.round(rgb.r * factor));
  const g = Math.min(255, Math.round(rgb.g * factor));
  const b = Math.min(255, Math.round(rgb.b * factor));
  
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/**
 * Common color palette with contrast information
 */
export const colorPalette = {
  // Primary colors
  primary: {
    blue: '#3B82F6',
    green: '#10B981',
    red: '#EF4444',
    yellow: '#F59E0B',
    purple: '#8B5CF6',
  },
  
  // Neutral colors
  neutral: {
    white: '#FFFFFF',
    black: '#000000',
    gray50: '#F9FAFB',
    gray100: '#F3F4F6',
    gray200: '#E5E7EB',
    gray300: '#D1D5DB',
    gray400: '#9CA3AF',
    gray500: '#6B7280',
    gray600: '#4B5563',
    gray700: '#374151',
    gray800: '#1F2937',
    gray900: '#111827',
  },
  
  // Get accessible text color for background
  getTextColor: (backgroundColor: string) => {
    return getContrastingTextColor(backgroundColor);
  },
  
  // Check contrast for a color combination
  checkContrast: (foreground: string, background: string) => {
    return checkWcagCompliance(foreground, background);
  },
};

/**
 * Generate accessible color combinations
 */
export function generateAccessibleCombinations(
  baseColor: string
): {
  background: string;
  text: string;
  border: string;
  hover: string;
  focus: string;
} {
  const textColor = getContrastingTextColor(baseColor);
  const borderColor = adjustColorForContrast(textColor, baseColor, 3);
  
  return {
    background: baseColor,
    text: textColor,
    border: borderColor,
    hover: adjustColorForContrast(baseColor, textColor, 3),
    focus: adjustColorForContrast(baseColor, textColor, 4.5),
  };
}