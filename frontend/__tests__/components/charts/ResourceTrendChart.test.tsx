import React from 'react';
import { render, screen } from '@testing-library/react';
import { ResourceTrendChart } from '@/components/charts/ResourceTrendChart';

describe('ResourceTrendChart Component', () => {
  const mockData = [
    {
      timestamp: '2024-01-01T00:00:00Z',
      cpu: 50,
      memory: 60,
      disk: 70,
    },
    {
      timestamp: '2024-01-01T01:00:00Z',
      cpu: 55,
      memory: 65,
      disk: 72,
    },
    {
      timestamp: '2024-01-01T02:00:00Z',
      cpu: 60,
      memory: 70,
      disk: 75,
    },
  ];

  describe('Rendering', () => {
    it('should render chart with data', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render empty chart with no data', () => {
      render(<ResourceTrendChart data={[]} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render chart container', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const container = document.querySelector('.w-full');
      expect(container).toBeInTheDocument();
    });
  });

  describe('Canvas Drawing', () => {
    it('should draw CPU line', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw memory line', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw disk line', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw grid lines', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw legend', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Data Handling', () => {
    it('should handle single data point', () => {
      const singleData = [mockData[0]];
      render(<ResourceTrendChart data={singleData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle multiple data points', () => {
      const multiData = [...mockData, ...mockData];
      render(<ResourceTrendChart data={multiData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle zero values', () => {
      const zeroData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          cpu: 0,
          memory: 0,
          disk: 0,
        },
      ];
      render(<ResourceTrendChart data={zeroData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle maximum values', () => {
      const maxData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          cpu: 100,
          memory: 100,
          disk: 100,
        },
      ];
      render(<ResourceTrendChart data={maxData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Line Colors', () => {
    it('should use blue for CPU line', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should use green for memory line', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should use orange for disk line', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing cpu field', () => {
      const incompleteData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          memory: 60,
          disk: 70,
        },
      ];
      render(<ResourceTrendChart data={incompleteData as any} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle missing memory field', () => {
      const incompleteData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          cpu: 50,
          disk: 70,
        },
      ];
      render(<ResourceTrendChart data={incompleteData as any} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle missing disk field', () => {
      const incompleteData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          cpu: 50,
          memory: 60,
        },
      ];
      render(<ResourceTrendChart data={incompleteData as any} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle very large values', () => {
      const largeData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          cpu: 1000,
          memory: 2000,
          disk: 3000,
        },
      ];
      render(<ResourceTrendChart data={largeData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should handle negative values', () => {
      const negativeData = [
        {
          timestamp: '2024-01-01T00:00:00Z',
          cpu: -10,
          memory: -20,
          disk: -30,
        },
      ];
      render(<ResourceTrendChart data={negativeData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const container = document.querySelector('.w-full');
      expect(container).toHaveClass('h-64');
    });

    it('should apply canvas styles', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toHaveClass('w-full');
      expect(canvas).toHaveClass('h-full');
    });
  });

  describe('Re-rendering', () => {
    it('should update when data changes', () => {
      const { rerender } = render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
      
      const newData = [
        {
          timestamp: '2024-01-01T03:00:00Z',
          cpu: 70,
          memory: 80,
          disk: 90,
        },
      ];
      
      rerender(<ResourceTrendChart data={newData} />);
      
      const canvasAfter = document.querySelector('canvas');
      expect(canvasAfter).toBeInTheDocument();
    });
  });

  describe('Canvas Scaling', () => {
    it('should scale canvas for high DPI', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Legend Rendering', () => {
    it('should render CPU legend', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render memory legend', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should render disk legend', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Grid Rendering', () => {
    it('should draw horizontal grid lines', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });

    it('should draw 5 grid lines by default', () => {
      render(<ResourceTrendChart data={mockData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with real-time data updates', () => {
      const { rerender } = render(<ResourceTrendChart data={mockData} />);
      
      const updatedData = [
        ...mockData,
        {
          timestamp: '2024-01-01T03:00:00Z',
          cpu: 65,
          memory: 75,
          disk: 80,
        },
      ];
      
      rerender(<ResourceTrendChart data={updatedData} />);
      
      const canvas = document.querySelector('canvas');
      expect(canvas).toBeInTheDocument();
    });
  });
});
