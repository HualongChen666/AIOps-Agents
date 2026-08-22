import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import DashboardPage from '@/app/dashboard/page';

// Mock the store
jest.mock('@/store/dashboard', () => ({
  useDashboardStore: jest.fn(() => ({
    stats: {
      alertCount: 0,
      healSuccessRate: 0,
      mttr: 0,
      availability: 0,
    },
    setStats: jest.fn(),
    updateStat: jest.fn(),
  })),
}));

// Mock the components
jest.mock('@/components/DashboardCards', () => ({
  DashboardCards: () => <div data-testid="dashboard-cards">Dashboard Cards</div>,
}));

jest.mock('@/components/AlertStream', () => ({
  AlertStream: () => <div data-testid="alert-stream">Alert Stream</div>,
}));

jest.mock('@/components/charts/ResourceTrendChart', () => ({
  ResourceTrendChart: ({ data }: { data: any[] }) => (
    <div data-testid="resource-trend-chart">
      Resource Trend Chart ({data.length} points)
    </div>
  ),
}));

jest.mock('@/components/charts/HealTimeline', () => ({
  HealTimeline: ({ events }: { events: any[] }) => (
    <div data-testid="heal-timeline">
      Heal Timeline ({events.length} events)
    </div>
  ),
}));

// Mock React Query
jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  })),
}));

// Mock API
jest.mock('@/lib/api', () => ({
  default: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render the dashboard page with title', () => {
      render(<DashboardPage />);

      expect(screen.getByText('仪表盘')).toBeInTheDocument();
    });

    it('should render subtitle', () => {
      render(<DashboardPage />);

      expect(screen.getByText('系统总览与实时监控')).toBeInTheDocument();
    });

    it('should render refresh button', () => {
      render(<DashboardPage />);

      expect(screen.getByText('刷新')).toBeInTheDocument();
    });

    it('should render dashboard cards component', () => {
      render(<DashboardPage />);

      expect(screen.getByTestId('dashboard-cards')).toBeInTheDocument();
    });

    it('should render alert stream component', () => {
      render(<DashboardPage />);

      expect(screen.getByTestId('alert-stream')).toBeInTheDocument();
    });

    it('should render resource trend chart', () => {
      render(<DashboardPage />);

      expect(screen.getByTestId('resource-trend-chart')).toBeInTheDocument();
    });

    it('should render heal timeline', () => {
      render(<DashboardPage />);

      expect(screen.getByTestId('heal-timeline')).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('should show loading state while fetching summary data', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockImplementation(() => ({
        data: null,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      }));

      render(<DashboardPage />);

      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });

    it('should hide loading state after data is loaded', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockImplementation(() => ({
        data: { total_alerts: 15 },
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      }));

      render(<DashboardPage />);

      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });
  });

  describe('Error States', () => {
    it('should show error state when API fails', () => {
      const { useQuery } = require('@tanstack/react-query');
      useQuery.mockImplementation(() => ({
        data: null,
        isLoading: false,
        error: new Error('API Error'),
        refetch: jest.fn(),
      }));

      render(<DashboardPage />);

      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });
  });

  describe('Real-time Alerts Section', () => {
    it('should display real-time alerts card', () => {
      render(<DashboardPage />);

      expect(screen.getByText('实时告警')).toBeInTheDocument();
    });
  });

  describe('Resource Trend Section', () => {
    it('should display resource trend card', () => {
      render(<DashboardPage />);

      expect(screen.getByText('资源使用趋势')).toBeInTheDocument();
    });
  });

  describe('Heal Activity Section', () => {
    it('should display heal activity card', () => {
      render(<DashboardPage />);

      expect(screen.getByText('修复活动')).toBeInTheDocument();
    });
  });

  describe('Refresh Functionality', () => {
    it('should refresh data when refresh button is clicked', () => {
      const { useQuery } = require('@tanstack/react-query');
      const mockRefetch = jest.fn();
      useQuery.mockImplementation(() => ({
        data: null,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      }));

      render(<DashboardPage />);

      const refreshButton = screen.getByText('刷新');
      fireEvent.click(refreshButton);

      expect(mockRefetch).toHaveBeenCalled();
    });
  });
});
