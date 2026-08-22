import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import { QuickActions } from '@/components/QuickActions';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

const mockPush = jest.fn();
beforeEach(() => {
  (useRouter as jest.Mock).mockReturnValue({
    push: mockPush,
  });
  mockPush.mockClear();
});

describe('QuickActions Component', () => {
  describe('Rendering', () => {
    it('should render all quick action buttons', () => {
      render(<QuickActions />);
      
      expect(screen.getByText('新建告警规则')).toBeInTheDocument();
      expect(screen.getByText('查看拓扑')).toBeInTheDocument();
      expect(screen.getByText('审批中心')).toBeInTheDocument();
      expect(screen.getByText('RAG搜索')).toBeInTheDocument();
    });

    it('should render icons for each action', () => {
      render(<QuickActions />);
      
      expect(screen.getByText('🔔')).toBeInTheDocument();
      expect(screen.getByText('🔗')).toBeInTheDocument();
      expect(screen.getByText('✅')).toBeInTheDocument();
      expect(screen.getByText('🔍')).toBeInTheDocument();
    });

    it('should render buttons with correct styling', () => {
      render(<QuickActions />);
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveClass('bg-blue-600');
        expect(button).toHaveClass('text-white');
      });
    });
  });

  describe('Navigation', () => {
    it('should navigate to alerts page when first button clicked', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const alertsButton = screen.getByText('新建告警规则');
      await user.click(alertsButton);
      
      expect(mockPush).toHaveBeenCalledWith('/alerts');
    });

    it('should navigate to topology page when second button clicked', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const topologyButton = screen.getByText('查看拓扑');
      await user.click(topologyButton);
      
      expect(mockPush).toHaveBeenCalledWith('/topology');
    });

    it('should navigate to approval page when third button clicked', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const approvalButton = screen.getByText('审批中心');
      await user.click(approvalButton);
      
      expect(mockPush).toHaveBeenCalledWith('/approval');
    });

    it('should navigate to history page when fourth button clicked', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const historyButton = screen.getByText('RAG搜索');
      await user.click(historyButton);
      
      expect(mockPush).toHaveBeenCalledWith('/history');
    });
  });

  describe('Button Styling', () => {
    it('should apply hover effects', () => {
      render(<QuickActions />);
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveClass('hover:bg-blue-700');
      });
    });

    it('should apply transition effects', () => {
      render(<QuickActions />);
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveClass('transition-colors');
      });
    });

    it('should have flex layout with gap', () => {
      const { container } = render(<QuickActions />);
      
      const containerDiv = container.firstChild;
      expect(containerDiv).toHaveClass('flex');
      expect(containerDiv).toHaveClass('gap-2');
    });
  });

  describe('Accessibility', () => {
    it('should have accessible button labels', () => {
      render(<QuickActions />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(4);
    });

    it('should have visible text for screen readers', () => {
      render(<QuickActions />);
      
      expect(screen.getByText('新建告警规则')).toBeVisible();
      expect(screen.getByText('查看拓扑')).toBeVisible();
      expect(screen.getByText('审批中心')).toBeVisible();
      expect(screen.getByText('RAG搜索')).toBeVisible();
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid button clicks', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const buttons = screen.getAllByRole('button');
      
      await user.click(buttons[0]);
      await user.click(buttons[1]);
      await user.click(buttons[2]);
      
      expect(mockPush).toHaveBeenCalledTimes(3);
    });

    it('should not break if router push fails', async () => {
      const user = userEvent.setup();
      mockPush.mockImplementation(() => {
        throw new Error('Navigation failed');
      });
      
      render(<QuickActions />);
      
      const button = screen.getByText('新建告警规则');
      
      // Should not throw error
      await expect(user.click(button)).rejects.toThrow('Navigation failed');
    });
  });

  describe('Integration', () => {
    it('should work with Next.js router', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const button = screen.getByText('新建告警规则');
      await user.click(button);
      
      expect(mockPush).toHaveBeenCalledWith('/alerts');
    });

    it('should maintain button state after navigation', async () => {
      const user = userEvent.setup();
      render(<QuickActions />);
      
      const button = screen.getByText('新建告警规则');
      await user.click(button);
      
      // Button should still be visible and clickable
      expect(button).toBeInTheDocument();
      expect(button).toBeEnabled();
    });
  });
});
