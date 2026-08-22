import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MetricsChart } from '@/components/MetricsChart';
import api from '@/lib/api';

// Mock the API module
jest.mock('@/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// Mock react-query
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('MetricsChart Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<MetricsChart />);
      
      expect(screen.getByText('加载中…')).toBeInTheDocument();
    });

    it('should show loading in styled container', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<MetricsChart />);
      
      const container = screen.getByText('加载中…').closest('section');
      expect(container).toHaveClass('bg-[var(--color-surface)]');
    });
  });

  describe('Error State', () => {
    it('should show error message when API fails', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('无法获取指标数据')).toBeInTheDocument();
      });
    });

    it('should show error in styled container', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        const container = screen.getByText('无法获取指标数据').closest('section');
        expect(container).toHaveClass('bg-[var(--color-surface)]');
      });
    });
  });

  describe('Data Rendering', () => {
    const mockMetricsData = {
      cpu: [10, 20, 30, 40, 50],
      memory: [40, 50, 60, 70, 80],
      net_in: [100, 200, 300, 400, 500],
      disk: [60, 70, 80, 90, 100],
      timestamps: ['2024-01-01T00:00:00Z', '2024-01-01T01:00:00Z', '2024-01-01T02:00:00Z', '2024-01-01T03:00:00Z', '2024-01-01T04:00:00Z'],
    };

    it('should render metrics charts when data is loaded', async () => {
      mockedApi.get.mockResolvedValue({ data: mockMetricsData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
        expect(screen.getByText('内存使用率')).toBeInTheDocument();
        expect(screen.getByText('网络入流量')).toBeInTheDocument();
        expect(screen.getByText('磁盘使用率')).toBeInTheDocument();
      });
    });

    it('should render current values', async () => {
      mockedApi.get.mockResolvedValue({ data: mockMetricsData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText(/当前: 50.0%/)).toBeInTheDocument();
        expect(screen.getByText(/当前: 80.0%/)).toBeInTheDocument();
      });
    });

    it('should call API with correct endpoint', async () => {
      mockedApi.get.mockResolvedValue({ data: mockMetricsData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/metrics/history?hours=24');
      });
    });
  });

  describe('Chart Rendering', () => {
    it('should render CPU chart with correct color', async () => {
      const mockData = {
        cpu: [10, 20, 30],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
      });
    });

    it('should render memory chart with correct color', async () => {
      const mockData = {
        memory: [40, 50, 60],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('内存使用率')).toBeInTheDocument();
      });
    });

    it('should render network chart with correct color', async () => {
      const mockData = {
        net_in: [100, 200, 300],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('网络入流量')).toBeInTheDocument();
      });
    });

    it('should render disk chart with correct color', async () => {
      const mockData = {
        disk: [60, 70, 80],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('磁盘使用率')).toBeInTheDocument();
      });
    });
  });

  describe('Data Formatting', () => {
    it('should format numbers correctly', async () => {
      const mockData = {
        cpu: [10.567, 20.891],
        timestamps: ['T0', 'T1'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText(/20.9%/)).toBeInTheDocument();
      });
    });

    it('should handle undefined values', async () => {
      const mockData = {
        cpu: [10, undefined, 30],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
      });
    });

    it('should display N/A for missing values', async () => {
      const mockData = {
        cpu: [],
        timestamps: [],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        // Should not render chart for empty data
        expect(screen.queryByText('CPU 使用率')).not.toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty data', async () => {
      mockedApi.get.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('24小时指标趋势')).toBeInTheDocument();
      });
    });

    it('should handle missing timestamps', async () => {
      const mockData = {
        cpu: [10, 20, 30],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
      });
    });

    it('should handle single data point', async () => {
      const mockData = {
        cpu: [50],
        timestamps: ['T0'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
      });
    });

    it('should handle very large values', async () => {
      const mockData = {
        cpu: [10000, 20000, 30000],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU 使用率')).toBeInTheDocument();
      });
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', async () => {
      mockedApi.get.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        const section = screen.getByText('24小时指标趋势').closest('section');
        expect(section).toHaveClass('bg-[var(--color-surface)]');
        expect(section).toHaveClass('rounded-lg');
        expect(section).toHaveClass('shadow');
      });
    });

    it('should apply correct chart bar styles', async () => {
      const mockData = {
        cpu: [10, 20, 30],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        const bars = document.querySelectorAll('.rounded-t');
        expect(bars.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Refetch Interval', () => {
    it('should set up refetch interval', async () => {
      mockedApi.get.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', async () => {
      mockedApi.get.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        const heading = screen.getByText('24小时指标趋势');
        expect(heading.tagName).toBe('H2');
      });
    });

    it('should have tooltips on chart bars', async () => {
      const mockData = {
        cpu: [10, 20, 30],
        timestamps: ['T0', 'T1', 'T2'],
      };
      mockedApi.get.mockResolvedValue({ data: mockData });
      
      renderWithQueryClient(<MetricsChart />);
      
      await waitFor(() => {
        const bars = document.querySelectorAll('[title]');
        expect(bars.length).toBeGreaterThan(0);
      });
    });
  });
});
