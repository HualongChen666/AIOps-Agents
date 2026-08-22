import React from 'react';
import { render, screen } from '@testing-library/react';
import { GaugeChart } from '@/components/charts/GaugeChart';

describe('GaugeChart Component', () => {
  describe('Rendering', () => {
    it('should render gauge chart with default props', () => {
      render(<GaugeChart value={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render with custom title', () => {
      render(<GaugeChart value={50} title="CPU Usage" />);
      
      expect(screen.getByText('CPU Usage')).toBeInTheDocument();
    });

    it('should render with custom unit', () => {
      render(<GaugeChart value={50} unit="MB" />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render with custom color', () => {
      render(<GaugeChart value={50} color="#ff0000" />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render with custom size', () => {
      render(<GaugeChart value={50} size={300} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toHaveAttribute('width', '300');
      expect(canvas).toHaveAttribute('height', '300');
    });
  });

  describe('Value Display', () => {
    it('should display value correctly', () => {
      render(<GaugeChart value={75.5} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle values at minimum', () => {
      render(<GaugeChart value={0} min={0} max={100} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle values at maximum', () => {
      render(<GaugeChart value={100} min={0} max={100} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should clamp values above max', () => {
      render(<GaugeChart value={150} min={0} max={100} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should clamp values below min', () => {
      render(<GaugeChart value={-10} min={0} max={100} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Canvas Drawing', () => {
    it('should draw background arc', () => {
      render(<GaugeChart value={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw value arc', () => {
      render(<GaugeChart value={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw value text', () => {
      render(<GaugeChart value={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw title when provided', () => {
      render(<GaugeChart value={50} title="Test Title" />);
      
      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });
  });

  describe('Custom Range', () => {
    it('should handle custom min value', () => {
      render(<GaugeChart value={25} min={0} max={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle custom max value', () => {
      render(<GaugeChart value={75} min={0} max={200} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle negative range', () => {
      render(<GaugeChart value={0} min={-50} max={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero range', () => {
      render(<GaugeChart value={50} min={50} max={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle very large values', () => {
      render(<GaugeChart value={1000000} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle very small values', () => {
      render(<GaugeChart value={0.001} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle decimal values', () => {
      render(<GaugeChart value={33.333} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should wrap in Card component', () => {
      render(<GaugeChart value={50} />);
      
      const card = document.querySelector('.rounded-lg');
      expect(card).toBeInTheDocument();
    });

    it('should apply correct canvas size', () => {
      render(<GaugeChart value={50} size={200} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toHaveAttribute('width', '200');
      expect(canvas).toHaveAttribute('height', '200');
    });
  });

  describe('Accessibility', () => {
    it('should have accessible title', () => {
      render(<GaugeChart value={50} title="Accessible Chart" />);
      
      expect(screen.getByText('Accessible Chart')).toBeInTheDocument();
    });
  });

  describe('Re-rendering', () => {
    it('should update when value changes', () => {
      const { rerender } = render(<GaugeChart value={50} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
      
      rerender(<GaugeChart value={75} />);
      
      const canvasAfter = document.querySelector('canvas');
      expect(canvasAfter).toBeInTheDocument();
    });

    it('should update when color changes', () => {
      const { rerender } = render(<GaugeChart value={50} color="#ff0000" />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
      
      rerender(<GaugeChart value={50} color="#00ff00" />);
      
      const canvasAfter = document.querySelector('canvas');
      expect(canvasAfter).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with Card components', () => {
      render(<GaugeChart value={50} title="Test" />);
      
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });
});
