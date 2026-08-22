import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HistoryFilters } from '@/components/HistoryFilters';

describe('HistoryFilters Component', () => {
  describe('Rendering', () => {
    it('should render filter component with all filters', () => {
      render(<HistoryFilters />);

      expect(screen.getByText('查询类型')).toBeInTheDocument();
      expect(screen.getByText('时间范围')).toBeInTheDocument();
      expect(screen.getByText('严重程度')).toBeInTheDocument();
      expect(screen.getByText('状态')).toBeInTheDocument();
      expect(screen.getByText('重置')).toBeInTheDocument();
      expect(screen.getByText('应用筛选')).toBeInTheDocument();
    });

    it('should render query type select with correct options', () => {
      render(<HistoryFilters />);

      expect(screen.getAllByText('全部').length).toBeGreaterThan(0);
      expect(screen.getByText('告警')).toBeInTheDocument();
      expect(screen.getByText('修复')).toBeInTheDocument();
      expect(screen.getByText('审批')).toBeInTheDocument();
    });

    it('should render time range select with correct options', () => {
      render(<HistoryFilters />);

      expect(screen.getByText('最近1小时')).toBeInTheDocument();
      expect(screen.getByText('最近24小时')).toBeInTheDocument();
      expect(screen.getByText('最近7天')).toBeInTheDocument();
      expect(screen.getByText('最近30天')).toBeInTheDocument();
      expect(screen.getByText('最近90天')).toBeInTheDocument();
    });

    it('should render severity select with correct options', () => {
      render(<HistoryFilters />);

      expect(screen.getAllByText('全部').length).toBeGreaterThan(0);
      expect(screen.getByText('P0 - 严重')).toBeInTheDocument();
      expect(screen.getByText('P1 - 高')).toBeInTheDocument();
      expect(screen.getByText('P2 - 中')).toBeInTheDocument();
      expect(screen.getByText('P3 - 低')).toBeInTheDocument();
    });

    it('should render status select with correct options', () => {
      render(<HistoryFilters />);

      expect(screen.getAllByText('全部').length).toBeGreaterThan(0);
      expect(screen.getByText('成功')).toBeInTheDocument();
      expect(screen.getByText('失败')).toBeInTheDocument();
      expect(screen.getByText('待处理')).toBeInTheDocument();
    });

    it('should have default values', () => {
      render(<HistoryFilters />);

      const selects = screen.getAllByRole('combobox');
      expect(selects[0]).toHaveValue('all');
      expect(selects[1]).toHaveValue('24h');
      expect(selects[2]).toHaveValue('all');
      expect(selects[3]).toHaveValue('all');
    });
  });

  describe('Filter State Management', () => {
    it('should update query type filter on change', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const queryTypeSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(queryTypeSelect, 'alerts');

      expect(queryTypeSelect).toHaveValue('alerts');
    });

    it('should update time range filter on change', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const timeRangeSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(timeRangeSelect, '7d');

      expect(timeRangeSelect).toHaveValue('7d');
    });

    it('should update severity filter on change', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const severitySelect = screen.getAllByRole('combobox')[2];
      await user.selectOptions(severitySelect, 'P0');

      expect(severitySelect).toHaveValue('P0');
    });

    it('should update status filter on change', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const statusSelect = screen.getAllByRole('combobox')[3];
      await user.selectOptions(statusSelect, 'success');

      expect(statusSelect).toHaveValue('success');
    });
  });

  describe('Filter Change Callback', () => {
    it('should call onFilterChange when query type changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const queryTypeSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(queryTypeSelect, 'repairs');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ queryType: 'repairs' })
      );
    });

    it('should call onFilterChange when time range changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const timeRangeSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(timeRangeSelect, '30d');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ timeRange: '30d' })
      );
    });

    it('should call onFilterChange when severity changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const severitySelect = screen.getAllByRole('combobox')[2];
      await user.selectOptions(severitySelect, 'P1');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ severity: 'P1' })
      );
    });

    it('should call onFilterChange when status changes', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const statusSelect = screen.getAllByRole('combobox')[3];
      await user.selectOptions(statusSelect, 'failure');

      expect(handleFilterChange).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'failure' })
      );
    });

    it('should not call onFilterChange when not provided', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const queryTypeSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(queryTypeSelect, 'alerts');

      // Should not throw error
      expect(queryTypeSelect).toHaveValue('alerts');
    });
  });

  describe('Button Interactions', () => {
    it('should render reset button', () => {
      render(<HistoryFilters />);
      const resetButton = screen.getByText('重置');
      expect(resetButton).toBeInTheDocument();
      expect(resetButton).toBeInstanceOf(HTMLButtonElement);
    });

    it('should render apply button', () => {
      render(<HistoryFilters />);
      const applyButton = screen.getByText('应用筛选');
      expect(applyButton).toBeInTheDocument();
      expect(applyButton).toBeInstanceOf(HTMLButtonElement);
    });

    it('should handle reset button click', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const resetButton = screen.getByText('重置');
      await user.click(resetButton);

      expect(resetButton).toBeInTheDocument();
    });

    it('should handle apply button click', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const applyButton = screen.getByText('应用筛选');
      await user.click(applyButton);

      expect(applyButton).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', () => {
      render(<HistoryFilters />);
      const container = screen.getByText('查询类型').closest('div')?.parentElement?.parentElement;
      expect(container).toHaveClass('bg-white');
    });

    it('should apply correct label styles', () => {
      render(<HistoryFilters />);
      const label = screen.getByText('查询类型');
      expect(label).toHaveClass('text-sm');
      expect(label).toHaveClass('font-medium');
    });

    it('should apply correct select styles', () => {
      render(<HistoryFilters />);
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
      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const queryTypeSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(queryTypeSelect, 'alerts');
      await user.selectOptions(queryTypeSelect, 'repairs');
      await user.selectOptions(queryTypeSelect, 'approvals');

      expect(handleFilterChange).toHaveBeenCalledTimes(3);
    });

    it('should handle all filter combinations', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn();
      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const [queryTypeSelect, timeRangeSelect, severitySelect, statusSelect] =
        screen.getAllByRole('combobox');

      await user.selectOptions(queryTypeSelect, 'alerts');
      await user.selectOptions(timeRangeSelect, '7d');
      await user.selectOptions(severitySelect, 'P0');
      await user.selectOptions(statusSelect, 'success');

      expect(handleFilterChange).toHaveBeenCalledWith({
        queryType: 'alerts',
        timeRange: '7d',
        severity: 'P0',
        status: 'success',
      });
    });

    it('should handle undefined onFilterChange prop', () => {
      render(<HistoryFilters onFilterChange={undefined} />);
      expect(screen.getByText('查询类型')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper labels for selects', () => {
      render(<HistoryFilters />);

      const selects = screen.getAllByRole('combobox');
      expect(selects).toHaveLength(4);
    });

    it('should have accessible button labels', () => {
      render(<HistoryFilters />);

      const resetButton = screen.getByText('重置');
      const applyButton = screen.getByText('应用筛选');

      expect(resetButton).toBeVisible();
      expect(applyButton).toBeVisible();
    });
  });

  describe('Integration', () => {
    it('should maintain filter state across multiple changes', async () => {
      const user = userEvent.setup();
      render(<HistoryFilters />);

      const [queryTypeSelect, timeRangeSelect, severitySelect, statusSelect] =
        screen.getAllByRole('combobox');

      await user.selectOptions(queryTypeSelect, 'alerts');
      await user.selectOptions(timeRangeSelect, '24h');
      await user.selectOptions(severitySelect, 'P1');
      await user.selectOptions(statusSelect, 'pending');

      expect(queryTypeSelect).toHaveValue('alerts');
      expect(timeRangeSelect).toHaveValue('24h');
      expect(severitySelect).toHaveValue('P1');
      expect(statusSelect).toHaveValue('pending');
    });

    it('should work with parent component state management', async () => {
      const user = userEvent.setup();
      const handleFilterChange = jest.fn((filters) => {
        return filters;
      });

      render(<HistoryFilters onFilterChange={handleFilterChange} />);

      const queryTypeSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(queryTypeSelect, 'all');

      expect(handleFilterChange).toHaveBeenCalled();
    });
  });
});
