import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { DashboardCards } from '@/components/DashboardCards';

// Mock the API module
jest.mock('@/lib/api', () => ({
  default: {
    get: jest.fn(),
  },
}));

// Mock React Query
jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(),
}));

describe('DashboardCards Component', () => {
  const mockMetrics = [
    { key: 'Total Users', value: 1234, unit: 'users', level: 'normal' as const },
    { key: 'Active Sessions', value: 567, unit: 'sessions', level: 'normal' as const },
    { key: 'Error Rate', value: 2.5, unit: '%', level: 'warning' as const },
    { key: 'Response Time', value: 500, unit: 'ms', level: 'critical' as const },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render loading state', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: null,
        error: null,
        isLoading: true,
      });

      render(<DashboardCards />);
      expect(screen.getByText('加载中…')).toBeInTheDocument();
    });

    it('should render error state', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: null,
        error: new Error('API Error'),
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('获取指标失败')).toBeInTheDocument();
    });

    it('should render metrics cards when data is loaded', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('Total Users')).toBeInTheDocument();
      expect(screen.getByText('Active Sessions')).toBeInTheDocument();
      expect(screen.getByText('Error Rate')).toBeInTheDocument();
      expect(screen.getByText('Response Time')).toBeInTheDocument();
    });

    it('should render empty state when data is empty', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: [],
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const grid = document.querySelector('.grid');
      expect(grid).toBeInTheDocument();
      expect(grid).toBeEmptyDOMElement();
    });
  });

  describe('Metric Display', () => {
    it('should display metric key', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });

    it('should display metric value', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('1234')).toBeInTheDocument();
    });

    it('should display metric unit when provided', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('users')).toBeInTheDocument();
    });

    it('should not display unit when not provided', () => {
      const { useQuery } = require('@tanstack/react-query');
      const metricsWithoutUnit = [{ key: 'Count', value: 100, level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: metricsWithoutUnit,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('100')).toBeInTheDocument();
    });

    it('should handle string values', () => {
      const { useQuery } = require('@tanstack/react-query');
      const stringMetrics = [{ key: 'Status', value: 'Active', level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: stringMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('should handle decimal values', () => {
      const { useQuery } = require('@tanstack/react-query');
      const decimalMetrics = [{ key: 'Rate', value: 95.5, unit: '%', level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: decimalMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('95.5')).toBeInTheDocument();
    });
  });

  describe('Level Styling', () => {
    it('should apply normal level styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      const normalMetrics = [{ key: 'Normal', value: 100, level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: normalMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const card = screen.getByText('Normal').closest('div');
      expect(card).toHaveClass('border-gray-200', 'bg-white');
    });

    it('should apply warning level styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      const warningMetrics = [{ key: 'Warning', value: 100, level: 'warning' as const }];
      useQuery.mockReturnValue({
        data: warningMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const card = screen.getByText('Warning').closest('div');
      expect(card).toHaveClass('border-yellow-300', 'bg-yellow-50');
    });

    it('should apply critical level styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      const criticalMetrics = [{ key: 'Critical', value: 100, level: 'critical' as const }];
      useQuery.mockReturnValue({
        data: criticalMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const card = screen.getByText('Critical').closest('div');
      expect(card).toHaveClass('border-red-300', 'bg-red-50');
    });

    it('should apply default styling when level is not provided', () => {
      const { useQuery } = require('@tanstack/react-query');
      const noLevelMetrics = [{ key: 'No Level', value: 100 } as any];
      useQuery.mockReturnValue({
        data: noLevelMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const card = screen.getByText('No Level').closest('div');
      expect(card).toHaveClass('border-gray-200', 'bg-white');
    });
  });

  describe('Grid Layout', () => {
    it('should render with correct grid classes', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const grid = document.querySelector('.grid');
      expect(grid).toHaveClass('grid', 'grid-cols-1', 'sm:grid-cols-2', 'lg:grid-cols-4', 'gap-4');
    });

    it('should render all metrics in grid', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const cards = document.querySelectorAll('.grid > div');
      expect(cards).toHaveLength(4);
    });
  });

  describe('Card Styling', () => {
    it('should have correct card base styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const card = screen.getByText('Total Users').closest('div');
      expect(card).toHaveClass('p-4', 'rounded', 'shadow-sm', 'border');
    });

    it('should have correct title styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const title = screen.getByText('Total Users');
      expect(title).toHaveClass('text-sm', 'font-medium', 'text-gray-600', 'truncate');
    });

    it('should have correct value styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const value = screen.getByText('1234');
      expect(value).toHaveClass('text-2xl', 'font-semibold', 'text-gray-800');
    });

    it('should have correct unit styling', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const unit = screen.getByText('users');
      expect(unit).toHaveClass('text-base', 'font-medium');
    });
  });

  describe('Edge Cases', () => {
    it('should handle long metric keys', () => {
      const { useQuery } = require('@tanstack/react-query');
      const longKeyMetrics = [
        { key: 'This is a very long metric key that might need truncation', value: 100, level: 'normal' as const },
      ];
      useQuery.mockReturnValue({
        data: longKeyMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const title = screen.getByText(/This is a very long/);
      expect(title).toHaveClass('truncate');
    });

    it('should handle special characters in metric keys', () => {
      const { useQuery } = require('@tanstack/react-query');
      const specialKeyMetrics = [
        { key: 'Metric <special> & characters', value: 100, level: 'normal' as const },
      ];
      useQuery.mockReturnValue({
        data: specialKeyMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText(/Metric/)).toBeInTheDocument();
    });

    it('should handle unicode characters', () => {
      const { useQuery } = require('@tanstack/react-query');
      const unicodeMetrics = [
        { key: '用户总数', value: 1000, level: 'normal' as const },
      ];
      useQuery.mockReturnValue({
        data: unicodeMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('用户总数')).toBeInTheDocument();
    });

    it('should handle zero values', () => {
      const { useQuery } = require('@tanstack/react-query');
      const zeroMetrics = [{ key: 'Count', value: 0, level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: zeroMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should handle negative values', () => {
      const { useQuery } = require('@tanstack/react-query');
      const negativeMetrics = [{ key: 'Change', value: -50, level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: negativeMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('-50')).toBeInTheDocument();
    });

    it('should handle very large values', () => {
      const { useQuery } = require('@tanstack/react-query');
      const largeMetrics = [{ key: 'Big Number', value: 999999999, level: 'normal' as const }];
      useQuery.mockReturnValue({
        data: largeMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(screen.getByText('999999999')).toBeInTheDocument();
    });
  });

  describe('React Query Configuration', () => {
    it('should call useQuery with correct query key', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ['metrics'],
        })
      );
    });

    it('should have correct refetch interval', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          refetchInterval: 30000,
        })
      );
    });

    it('should have correct stale time', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      expect(useQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          staleTime: 20000,
        })
      );
    });
  });

  describe('Accessibility', () => {
    it('should have title attribute on metric key for truncation', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const title = screen.getByText('Total Users');
      expect(title).toHaveAttribute('title', 'Total Users');
    });

    it('should have proper heading structure', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const headings = screen.getAllByRole('heading');
      expect(headings).toHaveLength(4);
    });
  });

  describe('Integration Tests', () => {
    it('should handle data update', async () => {
      const { useQuery } = require('@tanstack/react-query');
      
      useQuery.mockReturnValue({
        data: [{ key: 'Initial', value: 100, level: 'normal' as const }],
        error: null,
        isLoading: false,
      });

      const { rerender } = render(<DashboardCards />);
      expect(screen.getByText('Initial')).toBeInTheDocument();

      useQuery.mockReturnValue({
        data: [{ key: 'Updated', value: 200, level: 'normal' as const }],
        error: null,
        isLoading: false,
      });

      rerender(<DashboardCards />);
      expect(screen.getByText('Updated')).toBeInTheDocument();
      expect(screen.queryByText('Initial')).not.toBeInTheDocument();
    });

    it('should handle transition from loading to data', () => {
      const { useQuery } = require('@tanstack/react-query');
      
      useQuery.mockReturnValue({
        data: null,
        error: null,
        isLoading: true,
      });

      const { rerender } = render(<DashboardCards />);
      expect(screen.getByText('加载中…')).toBeInTheDocument();

      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      rerender(<DashboardCards />);
      expect(screen.queryByText('加载中…')).not.toBeInTheDocument();
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });

    it('should handle transition from loading to error', () => {
      const { useQuery } = require('@tanstack/react-query');
      
      useQuery.mockReturnValue({
        data: null,
        error: null,
        isLoading: true,
      });

      const { rerender } = render(<DashboardCards />);
      expect(screen.getByText('加载中…')).toBeInTheDocument();

      useQuery.mockReturnValue({
        data: null,
        error: new Error('API Error'),
        isLoading: false,
      });

      rerender(<DashboardCards />);
      expect(screen.queryByText('加载中…')).not.toBeInTheDocument();
      expect(screen.getByText('获取指标失败')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should render grid container', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const grid = document.querySelector('.grid');
      expect(grid).toBeInTheDocument();
    });

    it('should render card for each metric', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const cards = document.querySelectorAll('.grid > div');
      expect(cards).toHaveLength(4);
    });

    it('should render heading inside each card', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockReturnValue({
        data: mockMetrics,
        error: null,
        isLoading: false,
      });

      render(<DashboardCards />);
      const headings = screen.getAllByRole('heading');
      expect(headings).toHaveLength(4);
    });
  });
});
