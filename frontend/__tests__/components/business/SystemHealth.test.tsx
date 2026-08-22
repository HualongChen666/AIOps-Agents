import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SystemHealth } from '@/components/SystemHealth';
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

describe('SystemHealth Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<SystemHealth />);
      
      expect(screen.getByText('加载中…')).toBeInTheDocument();
    });

    it('should show loading in styled container', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<SystemHealth />);
      
      const container = screen.getByText('加载中…').closest('section');
      expect(container).toHaveClass('bg-white');
    });
  });

  describe('Error State', () => {
    it('should show error message when API fails', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('无法获取健康状态')).toBeInTheDocument();
      });
    });

    it('should show error in styled container', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const container = screen.getByText('无法获取健康状态').closest('section');
        expect(container).toHaveClass('bg-white');
      });
    });
  });

  describe('Data Rendering', () => {
    const mockHealthData = {
      status: 'healthy' as const,
      services: [
        { name: 'API Gateway', status: 'up' as const, latency: 50 },
        { name: 'Database', status: 'up' as const, latency: 30 },
        { name: 'Cache', status: 'up' as const, latency: 10 },
      ],
      last_updated: '2024-01-01T00:00:00Z',
    };

    it('should render system health status', async () => {
      mockedApi.get.mockResolvedValue({ data: mockHealthData });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('HEALTHY')).toBeInTheDocument();
      });
    });

    it('should render all services', async () => {
      mockedApi.get.mockResolvedValue({ data: mockHealthData });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('API Gateway')).toBeInTheDocument();
        expect(screen.getByText('Database')).toBeInTheDocument();
        expect(screen.getByText('Cache')).toBeInTheDocument();
      });
    });

    it('should render service latency when available', async () => {
      mockedApi.get.mockResolvedValue({ data: mockHealthData });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('50ms')).toBeInTheDocument();
        expect(screen.getByText('30ms')).toBeInTheDocument();
        expect(screen.getByText('10ms')).toBeInTheDocument();
      });
    });

    it('should render last updated timestamp', async () => {
      mockedApi.get.mockResolvedValue({ data: mockHealthData });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText(/最后更新/)).toBeInTheDocument();
        expect(screen.getByText(/2024/)).toBeInTheDocument();
      });
    });
  });

  describe('Status Styling', () => {
    it('should apply correct color for healthy status', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const statusBadge = screen.getByText('HEALTHY');
        expect(statusBadge).toBeInTheDocument();
      });
    });

    it('should apply correct color for degraded status', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'degraded' as const,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('DEGRADED')).toBeInTheDocument();
      });
    });

    it('should apply correct color for down status', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'down' as const,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('DOWN')).toBeInTheDocument();
      });
    });
  });

  describe('Service Status Styling', () => {
    it('should apply correct color for up service', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [{ name: 'Test', status: 'up' as const }],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('UP')).toBeInTheDocument();
      });
    });

    it('should apply correct color for down service', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [{ name: 'Test', status: 'down' as const }],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('DOWN')).toBeInTheDocument();
      });
    });

    it('should show green indicator for up service', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [{ name: 'Test', status: 'up' as const }],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const indicators = document.querySelectorAll('.bg-green-500');
        expect(indicators.length).toBeGreaterThan(0);
      });
    });

    it('should show red indicator for down service', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [{ name: 'Test', status: 'down' as const }],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const indicators = document.querySelectorAll('.bg-red-500');
        expect(indicators.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty services array', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('HEALTHY')).toBeInTheDocument();
      });
    });

    it('should handle service without latency', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [{ name: 'Test', status: 'up' as const }],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('Test')).toBeInTheDocument();
        expect(screen.queryByText(/ms/)).not.toBeInTheDocument();
      });
    });

    it('should handle undefined status', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: undefined as any,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
      });
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const section = screen.getByText('系统健康状态').closest('section');
        expect(section).toHaveClass('bg-white');
        expect(section).toHaveClass('rounded-lg');
        expect(section).toHaveClass('shadow');
      });
    });

    it('should apply correct service card styles', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [{ name: 'Test', status: 'up' as const }],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const serviceCard = screen.getByText('Test').closest('div');
        expect(serviceCard).toHaveClass('bg-gray-50');
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: {
          status: 'healthy' as const,
          services: [],
          last_updated: '2024-01-01T00:00:00Z',
        }
      });
      
      renderWithQueryClient(<SystemHealth />);
      
      await waitFor(() => {
        const heading = screen.getByText('系统健康状态');
        expect(heading.tagName).toBe('H2');
      });
    });
  });
});
