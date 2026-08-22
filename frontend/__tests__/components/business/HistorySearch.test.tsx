import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HistorySearch } from '@/components/HistorySearch';
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

describe('HistorySearch Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<HistorySearch />);
      
      expect(screen.getByText('加载中…')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should show error message when API fails', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('获取历史记录失败')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no records', async () => {
      mockedApi.get.mockResolvedValue({ data: { total: 0, records: [] } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('暂无历史记录')).toBeInTheDocument();
      });
    });

    it('should show no results message when search matches nothing', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test output',
            time: '2024-01-01T00:00:00Z'
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Test')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText('搜索历史记录...');
      await userEvent.type(searchInput, 'nonexistent');
      
      await waitFor(() => {
        expect(screen.getByText('未找到匹配的历史记录')).toBeInTheDocument();
      });
    });
  });

  describe('Data Rendering', () => {
    const mockRecords = [
      {
        id: '1',
        script_name: 'Fix CPU',
        script_key: 'fix_cpu',
        output: 'CPU usage reduced',
        time: '2024-01-01T00:00:00Z',
        success: true,
        risk: 'low',
      },
      {
        id: '2',
        script_name: 'Fix Memory',
        script_key: 'fix_memory',
        output: 'Memory freed',
        time: '2024-01-02T00:00:00Z',
        success: false,
        risk: 'high',
      },
    ];

    it('should render history records', async () => {
      mockedApi.get.mockResolvedValue({ data: { total: 2, records: mockRecords } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Fix CPU')).toBeInTheDocument();
        expect(screen.getByText('Fix Memory')).toBeInTheDocument();
      });
    });

    it('should render search input', async () => {
      mockedApi.get.mockResolvedValue({ data: { total: 0, records: [] } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('搜索历史记录...');
        expect(searchInput).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    const mockRecords = [
      {
        id: '1',
        script_name: 'Fix CPU',
        script_key: 'fix_cpu',
        output: 'CPU usage reduced',
        time: '2024-01-01T00:00:00Z',
        success: true,
        risk: 'low',
      },
    ];

    it('should filter records by title', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { total: 1, records: mockRecords } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Fix CPU')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText('搜索历史记录...');
      await user.type(searchInput, 'CPU');
      
      expect(screen.getByText('Fix CPU')).toBeInTheDocument();
    });

    it('should filter records by description', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { total: 1, records: mockRecords } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Fix CPU')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText('搜索历史记录...');
      await user.type(searchInput, 'reduced');
      
      expect(screen.getByText('Fix CPU')).toBeInTheDocument();
    });

    it('should be case insensitive', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { total: 1, records: mockRecords } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Fix CPU')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText('搜索历史记录...');
      await user.type(searchInput, 'cpu');
      
      expect(screen.getByText('Fix CPU')).toBeInTheDocument();
    });
  });

  describe('Type Styling', () => {
    it('should apply correct color for repair type', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: true
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('REPAIR')).toBeInTheDocument();
      });
    });
  });

  describe('Status Styling', () => {
    it('should apply correct color for success status', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: true
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('success')).toBeInTheDocument();
      });
    });

    it('should apply correct color for failure status', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: false
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('failure')).toBeInTheDocument();
      });
    });
  });

  describe('Record Selection', () => {
    const mockRecords = [
      {
        id: '1',
        script_name: 'Fix CPU',
        script_key: 'fix_cpu',
        output: 'CPU usage reduced',
        time: '2024-01-01T00:00:00Z',
        success: true,
        risk: 'low',
      },
    ];

    it('should show record details when clicked', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { total: 1, records: mockRecords } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Fix CPU')).toBeInTheDocument();
      });
      
      const record = screen.getByText('Fix CPU').closest('div');
      await user.click(record!);
      
      await waitFor(() => {
        expect(screen.getByText('记录详情')).toBeInTheDocument();
      });
    });

    it('should hide record details when close button clicked', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { total: 1, records: mockRecords } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Fix CPU')).toBeInTheDocument();
      });
      
      const record = screen.getByText('Fix CPU').closest('div');
      await user.click(record!);
      
      await waitFor(() => {
        expect(screen.getByText('记录详情')).toBeInTheDocument();
      });
      
      const closeButton = screen.getByText('✕');
      await user.click(closeButton);
      
      await waitFor(() => {
        expect(screen.queryByText('记录详情')).not.toBeInTheDocument();
      });
    });
  });

  describe('Timestamp Formatting', () => {
    it('should format timestamp correctly', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: true
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText(/2024/)).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty search query', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: true
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('Test')).toBeInTheDocument();
      });
      
      const searchInput = screen.getByPlaceholderText('搜索历史记录...');
      await user.clear(searchInput);
      
      expect(screen.getByText('Test')).toBeInTheDocument();
    });

    it('should handle records with missing fields', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1',
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: true
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        expect(screen.getByText('修复操作')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have accessible search input', async () => {
      mockedApi.get.mockResolvedValue({ data: { total: 0, records: [] } });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText('搜索历史记录...');
        expect(searchInput).toBeInstanceOf(HTMLInputElement);
      });
    });

    it('should have clickable record items', async () => {
      mockedApi.get.mockResolvedValue({ 
        data: { 
          total: 1, 
          records: [{ 
            id: '1', 
            script_name: 'Test', 
            script_key: 'test',
            output: 'Test',
            time: '2024-01-01T00:00:00Z',
            success: true
          }] 
        } 
      });
      
      renderWithQueryClient(<HistorySearch />);
      
      await waitFor(() => {
        const record = screen.getByText('Test').closest('div');
        expect(record).toHaveClass('cursor-pointer');
      });
    });
  });
});
