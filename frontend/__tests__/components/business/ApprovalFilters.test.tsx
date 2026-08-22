import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalFilters } from '@/components/ApprovalFilters';

describe('ApprovalFilters Component', () => {
  describe('Rendering', () => {
    it('should render filter component with all filters', () => {
      render(<ApprovalFilters />);

      expect(screen.getByText('状态')).toBeInTheDocument();
      expect(screen.getByText('风险等级')).toBeInTheDocument();
      expect(screen.getByText('时间范围')).toBeInTheDocument();
      expect(screen.getByText('重置')).toBeInTheDocument();
      expect(screen.getByText('应用筛选')).toBeInTheDocument();
    });

    it('should render status select with correct options', () => {
      render(<ApprovalFilters />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      expect(statusSelect).toBeInTheDocument();

      expect(screen.getAllByText('全部').length).toBeGreaterThan(0);
      expect(screen.getByText('待审批')).toBeInTheDocument();
      expect(screen.getByText('已批准')).toBeInTheDocument();
      expect(screen.getByText('已拒绝')).toBeInTheDocument();
    });

    it('should render risk level select with correct options', () => {
      render(<ApprovalFilters />);

      expect(screen.getAllByText('全部').length).toBeGreaterThan(0);
      expect(screen.getByText('低')).toBeInTheDocument();
      expect(screen.getByText('中')).toBeInTheDocument();
      expect(screen.getByText('高')).toBeInTheDocument();
      expect(screen.getByText('严重')).toBeInTheDocument();
    });

    it('should render time range select with correct options', () => {
      render(<ApprovalFilters />);

      expect(screen.getByText('最近1小时')).toBeInTheDocument();
      expect(screen.getByText('最近24小时')).toBeInTheDocument();
      expect(screen.getByText('最近7天')).toBeInTheDocument();
      expect(screen.getByText('最近30天')).toBeInTheDocument();
    });

    it('should have default values', () => {
      render(<ApprovalFilters />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      expect(statusSelect).toHaveValue('pending');
    });
  });

  describe('Filter State Management', () => {
    it('should update status filter on change', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(statusSelect, 'approved');

      expect(statusSelect).toHaveValue('approved');
    });

    it('should update risk level filter on change', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const riskSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(riskSelect, 'high');

      expect(riskSelect).toHaveValue('high');
    });

    it('should update time range filter on change', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const timeSelect = screen.getAllByRole('combobox')[2];
      await user.selectOptions(timeSelect, '7d');

      expect(timeSelect).toHaveValue('7d');
    });
  });

  describe('Filter Change Callback', () => {
    it('should call onFilterChange when status changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<ApprovalFilters onFilterChange={handleFilterChange} />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(statusSelect, 'approved');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'approved' })
      );
    });

    it('should call onFilterChange when risk level changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<ApprovalFilters onFilterChange={handleFilterChange} />);

      const riskSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(riskSelect, 'critical');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ riskLevel: 'critical' })
      );
    });

    it('should call onFilterChange when time range changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<ApprovalFilters onFilterChange={handleFilterChange} />);

      const timeSelect = screen.getAllByRole('combobox')[2];
      await user.selectOptions(timeSelect, '30d');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ dateRange: '30d' })
      );
    });

    it('should not call onFilterChange when not provided', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(statusSelect, 'approved');

      // Should not throw error
      expect(statusSelect).toHaveValue('approved');
    });
  });

  describe('Button Interactions', () => {
    it('should render reset button', () => {
      render(<ApprovalFilters />);
      const resetButton = screen.getByText('重置');
      expect(resetButton).toBeInTheDocument();
      expect(resetButton).toBeInstanceOf(HTMLButtonElement);
    });

    it('should render apply button', () => {
      render(<ApprovalFilters />);
      const applyButton = screen.getByText('应用筛选');
      expect(applyButton).toBeInTheDocument();
      expect(applyButton).toBeInstanceOf(HTMLButtonElement);
    });

    it('should handle reset button click', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const resetButton = screen.getByText('重置');
      await user.click(resetButton);

      // Button should be clickable without error
      expect(resetButton).toBeInTheDocument();
    });

    it('should handle apply button click', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const applyButton = screen.getByText('应用筛选');
      await user.click(applyButton);

      // Button should be clickable without error
      expect(applyButton).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', () => {
      render(<ApprovalFilters />);
      const container = screen.getByText('状态').closest('div')?.parentElement?.parentElement;
      expect(container).toHaveClass('bg-white');
    });

    it('should apply correct label styles', () => {
      render(<ApprovalFilters />);
      const label = screen.getByText('状态');
      expect(label).toHaveClass('text-sm');
      expect(label).toHaveClass('font-medium');
    });

    it('should apply correct select styles', () => {
      render(<ApprovalFilters />);
      const select = screen.getAllByRole('combobox')[0];
      expect(select).toHaveClass('px-3');
      expect(select).toHaveClass('py-2');
      expect(select).toHaveClass('border');
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid filter changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<ApprovalFilters onFilterChange={handleFilterChange} />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(statusSelect, 'approved');
      await user.selectOptions(statusSelect, 'rejected');
      await user.selectOptions(statusSelect, 'all');

      expect(handleFilterChange).toHaveBeenCalledTimes(3);
    });

    it('should handle all filter combinations', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<ApprovalFilters onFilterChange={handleFilterChange} />);

      const [statusSelect, riskSelect, timeSelect] = screen.getAllByRole('combobox');

      await user.selectOptions(statusSelect, 'approved');
      await user.selectOptions(riskSelect, 'high');
      await user.selectOptions(timeSelect, '7d');

      expect(handleFilterChange).toHaveBeenCalledWith({
        status: 'approved',
        riskLevel: 'high',
        dateRange: '7d',
      });
    });

    it('should handle undefined onFilterChange prop', () => {
      render(<ApprovalFilters onFilterChange={undefined} />);
      expect(screen.getByText('状态')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper labels for selects', () => {
      render(<ApprovalFilters />);

      const selects = screen.getAllByRole('combobox');
      expect(selects).toHaveLength(3);
    });

    it('should have accessible button labels', () => {
      render(<ApprovalFilters />);

      const resetButton = screen.getByText('重置');
      const applyButton = screen.getByText('应用筛选');

      expect(resetButton).toBeVisible();
      expect(applyButton).toBeVisible();
    });
  });

  describe('Integration', () => {
    it('should maintain filter state across multiple changes', async () => {
      const user = userEvent.setup();
      render(<ApprovalFilters />);

      const [statusSelect, riskSelect, timeSelect] = screen.getAllByRole('combobox');

      await user.selectOptions(statusSelect, 'approved');
      await user.selectOptions(riskSelect, 'medium');
      await user.selectOptions(timeSelect, '24h');

      expect(statusSelect).toHaveValue('approved');
      expect(riskSelect).toHaveValue('medium');
      expect(timeSelect).toHaveValue('24h');
    });

    it('should work with parent component state management', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn((filters) => {
        // Simulate parent component handling
        return filters;
      });

      render(<ApprovalFilters onFilterChange={handleFilterChange} />);

      const statusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(statusSelect, 'pending');

      expect(handleFilterChange).toHaveBeenCalled();
    });
  });
});
