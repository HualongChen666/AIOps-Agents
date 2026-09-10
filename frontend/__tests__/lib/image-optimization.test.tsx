import React from 'react';
import { render, screen } from '@testing-library/react';
import { OptimizedImage, LazyImage } from '@/lib/image-optimization';

describe('lib/image-optimization', () => {
  describe('OptimizedImage', () => {
    it('renders an image with the given src and alt text', () => {
      render(<OptimizedImage src="/hero.png" alt="Hero" width={400} height={300} />);
      const img = screen.getByAltText('Hero');
      expect(img).toBeInTheDocument();
      expect(img.getAttribute('src')).toContain('hero.png');
    });

    it('applies the className and default sizes attribute', () => {
      render(
        <OptimizedImage
          src="/hero.png"
          alt="Hero"
          width={400}
          height={300}
          className="rounded-lg"
        />
      );
      const img = screen.getByAltText('Hero');
      expect(img).toHaveClass('rounded-lg');
      expect(img.getAttribute('sizes')).toContain('100vw');
    });

    it('forwards a custom sizes value', () => {
      render(
        <OptimizedImage src="/hero.png" alt="Hero" width={10} height={10} sizes="50vw" />
      );
      expect(screen.getByAltText('Hero').getAttribute('sizes')).toBe('50vw');
    });

    it('supports priority and fill props', () => {
      render(<OptimizedImage src="/hero.png" alt="Hero" fill priority />);
      expect(screen.getByAltText('Hero')).toBeInTheDocument();
    });
  });

  describe('LazyImage', () => {
    it('renders like OptimizedImage but without priority', () => {
      render(<LazyImage src="/chart.png" alt="Chart" width={200} height={100} />);
      const img = screen.getByAltText('Chart');
      expect(img).toBeInTheDocument();
      expect(img.getAttribute('src')).toContain('chart.png');
      // Non-priority images should carry the lazy loading attribute.
      expect(img.getAttribute('loading')).toBe('lazy');
    });
  });
});
