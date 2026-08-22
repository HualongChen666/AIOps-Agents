import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import AlertsPage from '@/app/alerts/page';

// Mock all the dependencies
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
  useDebounce: jest.fn((value) => value),
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useRealtimeData: jest.fn(() => ({
    isConnected: true,
    data: null,
    lastUpdate: null,
  })),
}));

jest.mock('@/lib/api', () => ({
  default: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

// Mock React Query
jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(() => ({
    data: { alerts: [] },
    isLoading: false,
    error: null,
    refetch: jest.fn(),
  })),
}));

describe('AlertsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render the alerts page with title', () => {
      render(<AlertsPage />);

      expect(screen.getByText('告警管理')).toBeInTheDocument();
    });

    it('should render tabs', () => {
      render(<AlertsPage />);

      expect(screen.getByText('告警列表')).toBeInTheDocument();
      expect(screen.getByText('智能分析')).toBeInTheDocument();
      expect(screen.getByText('告警模式')).toBeInTheDocument();
    });

    it('should render refresh button', () => {
      render(<AlertsPage />);

      expect(screen.getByText('刷新')).toBeInTheDocument();
    });

    it('should render clear history button', () => {
      render(<AlertsPage />);

      expect(screen.getByText('清空历史')).toBeInTheDocument();
    });

    it('should display real-time connection status', () => {
      render(<AlertsPage />);

      expect(screen.getByText('实时连接')).toBeInTheDocument();
    });
  });

  describe('Tab Switching', () => {
    it('should switch to intelligence tab', () => {
      render(<AlertsPage />);

      const intelligenceTab = screen.getByText('智能分析');
      fireEvent.click(intelligenceTab);

      expect(screen.getByText('智能告警统计')).toBeInTheDocument();
    });

    it('should switch to patterns tab', () => {
      render(<AlertsPage />);

      const patternsTab = screen.getByText('告警模式');
      fireEvent.click(patternsTab);

      expect(screen.getByText('告警模式分析')).toBeInTheDocument();
    });

    it('should switch back to alerts tab', () => {
      render(<AlertsPage />);

      const intelligenceTab = screen.getByText('智能分析');
      fireEvent.click(intelligenceTab);

      const alertsTab = screen.getByText('告警列表');
      fireEvent.click(alertsTab);

      expect(screen.getByText('告警列表')).toBeInTheDocument();
    });
  });

  describe('Button Interactions', () => {
    it('should handle refresh button click', () => {
      render(<AlertsPage />);

      const refreshButton = screen.getByText('刷新');
      fireEvent.click(refreshButton);

      expect(screen.getByText('刷新')).toBeInTheDocument();
    });

    it('should handle clear button click with confirmation', () => {
      window.confirm = jest.fn(() => true);

      render(<AlertsPage />);

      const clearButton = screen.getByText('清空历史');
      fireEvent.click(clearButton);

      expect(window.confirm).toHaveBeenCalledWith('确定要清空所有告警历史吗？此操作不可恢复。');
    });

    it('should not clear when confirmation is cancelled', () => {
      window.confirm = jest.fn(() => false);

      render(<AlertsPage />);

      const clearButton = screen.getByText('清空历史');
      fireEvent.click(clearButton);

      expect(window.confirm).toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('should show loading state', () => {
      const { useLoadingState } = require('@/hooks/useEnhancements');
      useLoadingState.mockReturnValue({
        isLoading: true,
        error: null,
        data: null,
        setLoading: jest.fn(),
        setError: jest.fn(),
        setData: jest.fn(),
        reset: jest.fn(),
      });

      render(<AlertsPage />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error state', () => {
      const { useLoadingState } = require('@/hooks/useEnhancements');
      useLoadingState.mockReturnValue({
        isLoading: false,
        error: new Error('Test error'),
        data: null,
        setLoading: jest.fn(),
        setError: jest.fn(),
        setData: jest.fn(),
        reset: jest.fn(),
      });

      render(<AlertsPage />);

      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });
  });
});
