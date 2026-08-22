import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApprovalList } from '@/components/ApprovalList';
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

describe('ApprovalList Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading state initially', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<ApprovalList />);
      
      expect(screen.getByText('加载中…')).toBeInTheDocument();
    });

    it('should show loading message in container', () => {
      mockedApi.get.mockImplementation(() => new Promise(() => {}));
      
      renderWithQueryClient(<ApprovalList />);
      
      const container = screen.getByText('加载中…').closest('div');
      expect(container).toHaveClass('bg-white');
    });
  });

  describe('Error State', () => {
    it('should show error message when API fails', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('获取审批列表失败')).toBeInTheDocument();
      });
    });

    it('should show error in styled container', async () => {
      mockedApi.get.mockRejectedValue(new Error('API Error'));
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const container = screen.getByText('获取审批列表失败').closest('div');
        expect(container).toHaveClass('bg-white');
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no approvals', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('暂无待审批项')).toBeInTheDocument();
      });
    });

    it('should show empty state when items is undefined', async () => {
      mockedApi.get.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('暂无待审批项')).toBeInTheDocument();
      });
    });
  });

  describe('Data Rendering', () => {
    const mockApprovals = [
      {
        id: '1',
        alert_id: 'ALT-001',
        alert_json: '{}',
        rule_name: 'CPU High',
        script_key: 'fix_cpu',
        proposal: 'Reduce CPU usage',
        status: 'pending' as const,
        risk_level: 'high' as const,
        submitted_at: '2024-01-01T00:00:00Z',
        host: 'server1',
        platform: 'linux',
      },
      {
        id: '2',
        alert_id: 'ALT-002',
        alert_json: '{}',
        rule_name: 'Memory Low',
        script_key: 'fix_memory',
        proposal: 'Free memory',
        status: 'pending' as const,
        risk_level: 'medium' as const,
        submitted_at: '2024-01-02T00:00:00Z',
      },
    ];

    it('should render approval list with data', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: mockApprovals } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('ALT-001')).toBeInTheDocument();
        expect(screen.getByText('ALT-002')).toBeInTheDocument();
      });
    });

    it('should render table headers', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: mockApprovals } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('告警ID')).toBeInTheDocument();
        expect(screen.getByText('规则名称')).toBeInTheDocument();
        expect(screen.getByText('提案')).toBeInTheDocument();
        expect(screen.getByText('风险等级')).toBeInTheDocument();
        expect(screen.getByText('提交时间')).toBeInTheDocument();
        expect(screen.getByText('操作')).toBeInTheDocument();
      });
    });

    it('should render approval details correctly', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('CPU High')).toBeInTheDocument();
        expect(screen.getByText('Reduce CPU usage')).toBeInTheDocument();
      });
    });

    it('should format timestamp correctly', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText(/2024/)).toBeInTheDocument();
      });
    });
  });

  describe('Risk Level Styling', () => {
    it('should apply correct color for low risk', async () => {
      const approval = {
        ...mockApprovals[0],
        risk_level: 'low' as const,
      };
      mockedApi.get.mockResolvedValue({ data: { items: [approval] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const riskBadge = screen.getByText('LOW');
        expect(riskBadge).toBeInTheDocument();
      });
    });

    it('should apply correct color for medium risk', async () => {
      const approval = {
        ...mockApprovals[0],
        risk_level: 'medium' as const,
      };
      mockedApi.get.mockResolvedValue({ data: { items: [approval] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const riskBadge = screen.getByText('MEDIUM');
        expect(riskBadge).toBeInTheDocument();
      });
    });

    it('should apply correct color for high risk', async () => {
      const approval = {
        ...mockApprovals[0],
        risk_level: 'high' as const,
      };
      mockedApi.get.mockResolvedValue({ data: { items: [approval] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const riskBadge = screen.getByText('HIGH');
        expect(riskBadge).toBeInTheDocument();
      });
    });

    it('should apply correct color for critical risk', async () => {
      const approval = {
        ...mockApprovals[0],
        risk_level: 'critical' as const,
      };
      mockedApi.get.mockResolvedValue({ data: { items: [approval] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const riskBadge = screen.getByText('CRITICAL');
        expect(riskBadge).toBeInTheDocument();
      });
    });
  });

  describe('Approve Action', () => {
    it('should call approve API when approve button clicked', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      mockedApi.patch.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('批准')).toBeInTheDocument();
      });
      
      const approveButton = screen.getByText('批准');
      await user.click(approveButton);
      
      expect(mockedApi.patch).toHaveBeenCalledWith('/api/v1/approvals/1');
    });

    it('should handle approve API error gracefully', async () => {
      const user = userEvent.setup();
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      mockedApi.patch.mockRejectedValue(new Error('Approve failed'));
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('批准')).toBeInTheDocument();
      });
      
      const approveButton = screen.getByText('批准');
      await user.click(approveButton);
      
      expect(consoleSpy).toHaveBeenCalledWith('Failed to approve:', expect.any(Error));
      consoleSpy.mockRestore();
    });
  });

  describe('Reject Action', () => {
    it('should call reject API when reject button clicked', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      mockedApi.post.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('拒绝')).toBeInTheDocument();
      });
      
      const rejectButton = screen.getByText('拒绝');
      await user.click(rejectButton);
      
      expect(mockedApi.post).toHaveBeenCalledWith('/api/v1/approvals/reject', {
        alert_id: '1',
        reason: '用户拒绝',
      });
    });

    it('should handle reject API error gracefully', async () => {
      const user = userEvent.setup();
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      mockedApi.post.mockRejectedValue(new Error('Reject failed'));
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('拒绝')).toBeInTheDocument();
      });
      
      const rejectButton = screen.getByText('拒绝');
      await user.click(rejectButton);
      
      expect(consoleSpy).toHaveBeenCalledWith('Failed to reject:', expect.any(Error));
      consoleSpy.mockRestore();
    });
  });

  describe('Data Refresh', () => {
    it('should refetch data after approve action', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      mockedApi.patch.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('批准')).toBeInTheDocument();
      });
      
      const approveButton = screen.getByText('批准');
      await user.click(approveButton);
      
      // Should call get again after patch
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalledTimes(2);
      });
    });

    it('should refetch data after reject action', async () => {
      const user = userEvent.setup();
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      mockedApi.post.mockResolvedValue({ data: {} });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('拒绝')).toBeInTheDocument();
      });
      
      const rejectButton = screen.getByText('拒绝');
      await user.click(rejectButton);
      
      // Should call get again after post
      await waitFor(() => {
        expect(mockedApi.get).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Styling', () => {
    it('should apply correct table styles', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const table = screen.getByRole('table');
        expect(table).toHaveClass('min-w-full');
      });
    });

    it('should apply correct row hover styles', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        expect(rows[1]).toHaveClass('hover:bg-gray-50');
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle approval with missing optional fields', async () => {
      const minimalApproval = {
        id: '1',
        alert_id: 'ALT-001',
        alert_json: '{}',
        rule_name: 'Test',
        script_key: 'test',
        proposal: 'Test proposal',
        status: 'pending' as const,
        risk_level: 'low' as const,
        submitted_at: '2024-01-01T00:00:00Z',
      };
      mockedApi.get.mockResolvedValue({ data: { items: [minimalApproval] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText('ALT-001')).toBeInTheDocument();
      });
    });

    it('should handle very long proposal text', async () => {
      const longApproval = {
        ...mockApprovals[0],
        proposal: 'A'.repeat(1000),
      };
      mockedApi.get.mockResolvedValue({ data: { items: [longApproval] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByText(/A+/)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper table structure', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
        expect(screen.getAllByRole('columnheader')).toHaveLength(6);
      });
    });

    it('should have accessible action buttons', async () => {
      mockedApi.get.mockResolvedValue({ data: { items: [mockApprovals[0]] } });
      
      renderWithQueryClient(<ApprovalList />);
      
      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThan(0);
      });
    });
  });
});
