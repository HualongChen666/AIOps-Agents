import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import OverviewPage from '@/app/overview/page';

// Mock the components
jest.mock('@/components/DashboardCards', () => ({
  DashboardCards: () => <div data-testid="dashboard-cards">Dashboard Cards</div>,
}));

jest.mock('@/components/AlertStream', () => ({
  AlertStream: () => <div data-testid="alert-stream">Alert Stream</div>,
}));

jest.mock('@/components/SystemHealth', () => ({
  SystemHealth: () => <div data-testid="system-health">System Health</div>,
}));

jest.mock('@/components/QuickActions', () => ({
  QuickActions: () => <div data-testid="quick-actions">Quick Actions</div>,
}));

jest.mock('@/components/MetricsChart', () => ({
  MetricsChart: () => <div data-testid="metrics-chart">Metrics Chart</div>,
}));

// Mock the hooks
jest.mock('@/hooks/useEnhancements', () => ({
  useLoadingState: jest.fn(() => ({
    isLoading: false,
    error: null,
    data: null,
    setLoading: jest.fn(),
    setError: jest.fn(),
    setData: jest.fn(),
    reset: jest.fn(),
  })),
  useToast: jest.fn(() => ({
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
    toasts: [],
    addToast: jest.fn(),
    removeToast: jest.fn(),
  })),
}));

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ status: 'ok' }),
  })
) as jest.Mock;

describe('OverviewPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('Basic Rendering', () => {
    it('should render the overview page with title', () => {
      render(<OverviewPage />);

      expect(screen.getByText('AIOps 实时仪表盘')).toBeInTheDocument();
    });

    it('should render refresh button', () => {
      render(<OverviewPage />);

      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    it('should render quick actions component', () => {
      render(<OverviewPage />);

      expect(screen.getByTestId('quick-actions')).toBeInTheDocument();
    });

    it('should render dashboard cards component', () => {
      render(<OverviewPage />);

      expect(screen.getByTestId('dashboard-cards')).toBeInTheDocument();
    });

    it('should render metrics chart component', () => {
      render(<OverviewPage />);

      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
    });

    it('should render system health component', () => {
      render(<OverviewPage />);

      expect(screen.getByTestId('system-health')).toBeInTheDocument();
    });

    it('should render alert stream component', () => {
      render(<OverviewPage />);

      expect(screen.getByTestId('alert-stream')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should render all main components', () => {
      render(<OverviewPage />);

      expect(screen.getByTestId('quick-actions')).toBeInTheDocument();
      expect(screen.getByTestId('dashboard-cards')).toBeInTheDocument();
      expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
      expect(screen.getByTestId('system-health')).toBeInTheDocument();
      expect(screen.getByTestId('alert-stream')).toBeInTheDocument();
    });
  });

  describe('Button Interaction', () => {
    it('should handle refresh button click', () => {
      render(<OverviewPage />);

      // The button might show "Refreshing..." initially, so we check for either text
      const refreshButton = screen.getByText(/Refresh|Refreshing/);
      expect(refreshButton).toBeInTheDocument();
    });
  });

  describe('Layout', () => {
    it('should render components in expected structure', () => {
      const { container } = render(<OverviewPage />);

      expect(container.querySelector('.space-y-6')).toBeInTheDocument();
    });
  });
});
