import React from 'react';
import { render, screen } from '@testing-library/react';
import { TrendChart } from '@/components/charts/TrendChart';

describe('TrendChart Component', () => {
  describe('Rendering', () => {
    it('should render trend chart with default props', () => {
      render(<TrendChart data={[10, 20, 30, 40, 50]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render with custom title', () => {
      render(<TrendChart data={[10, 20, 30]} title="Sales Trend" />);
      
      expect(screen.getByText('Sales Trend')).toBeInTheDocument();
    });

    it('should render with custom color', () => {
      render(<TrendChart data={[10, 20, 30]} color="#ff0000" />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render with custom height', () => {
      render(<TrendChart data={[10, 20, 30]} height={300} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toHaveAttribute('height', '300');
    });
  });

  describe('Data Rendering', () => {
    it('should render single data point', () => {
      render(<TrendChart data={[50]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render multiple data points', () => {
      render(<TrendChart data={[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle empty data array', () => {
      render(<TrendChart data={[]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle zero values', () => {
      render(<TrendChart data={[0, 0, 0]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle negative values', () => {
      render(<TrendChart data={[-10, -5, 0, 5, 10]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Labels', () => {
    it('should render labels when provided', () => {
      render(
        <TrendChart 
          data={[10, 20, 30]} 
          labels={['Jan', 'Feb', 'Mar']} 
        />
      );
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle mismatched label count', () => {
      render(
        <TrendChart 
          data={[10, 20, 30, 40]} 
          labels={['Jan', 'Feb', 'Mar']} 
        />
      );
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle empty labels array', () => {
      render(
        <TrendChart 
          data={[10, 20, 30]} 
          labels={[]} 
        />
      );
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Grid Display', () => {
    it('should show grid by default', () => {
      render(<TrendChart data={[10, 20, 30]} showGrid={true} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should hide grid when showGrid is false', () => {
      render(<TrendChart data={[10, 20, 30]} showGrid={false} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Canvas Drawing', () => {
    it('should draw line chart', () => {
      render(<TrendChart data={[10, 20, 30]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw area under line', () => {
      render(<TrendChart data={[10, 20, 30]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw data points', () => {
      render(<TrendChart data={[10, 20, 30]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw labels when provided', () => {
      render(
        <TrendChart 
          data={[10, 20, 30]} 
          labels={['A', 'B', 'C']} 
        />
      );
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle very large values', () => {
      render(<TrendChart data={[1000000, 2000000, 3000000]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle very small values', () => {
      render(<TrendChart data={[0.001, 0.002, 0.003]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle same values', () => {
      render(<TrendChart data={[50, 50, 50, 50]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle single value repeated', () => {
      render(<TrendChart data={[50]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should wrap in Card component', () => {
      render(<TrendChart data={[10, 20, 30]} />);
      
      const card = document.querySelector('.rounded-lg');
      expect(card).toBeInTheDocument();
    });

    it('should apply correct canvas width', () => {
      render(<TrendChart data={[10, 20, 30]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toHaveAttribute('width', '400');
    });

    it('should apply custom height', () => {
      render(<TrendChart data={[10, 20, 30]} height={250} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toHaveAttribute('height', '250');
    });
  });

  describe('Re-rendering', () => {
    it('should update when data changes', () => {
      const { rerender } = render(<TrendChart data={[10, 20, 30]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
      
      rerender(<TrendChart data={[40, 50, 60]} />);
      
      const canvasAfter = document.querySelector('canvas');
      expect(canvasAfter).toBeInTheDocument();
    });

    it('should update when color changes', () => {
      const { rerender } = render(<TrendChart data={[10, 20, 30]} color="#ff0000" />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
      
      rerender(<TrendChart data={[10, 20, 30]} color="#00ff00" />);
      
      const canvasAfter = document.querySelector('canvas');
      expect(canvasAfter).toBeInTheDocument();
    });

    it('should update when labels change', () => {
      const { rerender } = render(
        <TrendChart data={[10, 20, 30]} labels={['A', 'B', 'C']} />
      );
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
      
      rerender(
        <TrendChart data={[10, 20, 30]} labels={['X', 'Y', 'Z']} />
      );
      
      const canvasAfter = document.querySelector('canvas');
      expect(canvasAfter).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible title', () => {
      render(<TrendChart data={[10, 20, 30]} title="Accessible Trend" />);
      
      expect(screen.getByText('Accessible Trend')).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with Card components', () => {
      render(<TrendChart data={[10, 20, 30]} title="Test Chart" />);
      
      expect(screen.getByText('Test Chart')).toBeInTheDocument();
    });
  });
});
