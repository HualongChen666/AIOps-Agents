import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DataTable } from '@/components/ui/DataTable';

// Mock the lucide-react icons
jest.mock('lucide-react', () => ({
  ChevronLeft: () => <span data-testid="chevron-left">←</span>,
  ChevronRight: () => <span data-testid="chevron-right">→</span>,
  Search: () => <span data-testid="search-icon">🔍</span>,
  Filter: () => <span data-testid="filter-icon">🔎</span>,
}));

describe('DataTable Component', () => {
  const mockData = [
    { id: 1, name: 'John Doe', status: 'Active', age: 30 },
    { id: 2, name: 'Jane Smith', status: 'Inactive', age: 25 },
    { id: 3, name: 'Bob Johnson', status: 'Active', age: 35 },
    { id: 4, name: 'Alice Brown', status: 'Pending', age: 28 },
    { id: 5, name: 'Charlie Wilson', status: 'Active', age: 40 },
  ];

  const mockColumns = [
    { key: 'id' as const, label: 'ID', sortable: true },
    { key: 'name' as const, label: 'Name', sortable: true, filterable: true },
    { key: 'status' as const, label: 'Status', sortable: true, filterable: true },
    { key: 'age' as const, label: 'Age', sortable: true },
  ];

  describe('Rendering', () => {
    it('should render table with data', () => {
      render(<DataTable data={mockData} columns={mockColumns} />);
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    });

    it('should render table headers', () => {
      render(<DataTable data={mockData} columns={mockColumns} />);
      expect(screen.getByText('ID')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Age')).toBeInTheDocument();
    });

    it('should render empty message when no data', () => {
      render(<DataTable data={[]} columns={mockColumns} />);
      expect(screen.getByText('暂无数据')).toBeInTheDocument();
    });

    it('should render custom empty message', () => {
      render(<DataTable data={[]} columns={mockColumns} emptyMessage="No records found" />);
      expect(screen.getByText('No records found')).toBeInTheDocument();
    });

    it('should render search input when searchable is true', () => {
      render(<DataTable data={mockData} columns={mockColumns} searchable />);
      expect(screen.getByPlaceholderText('搜索...')).toBeInTheDocument();
    });

    it('should not render search input when searchable is false', () => {
      render(<DataTable data={mockData} columns={mockColumns} searchable={false} />);
      expect(screen.queryByPlaceholderText('搜索...')).not.toBeInTheDocument();
    });

    it('should render filter dropdowns when filterable is true', () => {
      render(<DataTable data={mockData} columns={mockColumns} filterable />);
      expect(screen.getByText(/所有Name/)).toBeInTheDocument();
      expect(screen.getByText(/所有Status/)).toBeInTheDocument();
    });

    it('should not render filter dropdowns when filterable is false', () => {
      render(<DataTable data={mockData} columns={mockColumns} filterable={false} />);
      expect(screen.queryByText(/所有Name/)).not.toBeInTheDocument();
    });

    it('should render pagination when data exceeds page size', () => {
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} />);
      expect(screen.getByText(/第 1 /)).toBeInTheDocument();
      expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
    });

    it('should not render pagination when data fits on one page', () => {
      render(<DataTable data={mockData} columns={mockColumns} pageSize={10} />);
      expect(screen.queryByText(/第 1 /)).not.toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    it('should filter data based on search query', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} searchable />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      await user.type(searchInput, 'John');
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
    });

    it('should filter data case-insensitively', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} searchable />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      await user.type(searchInput, 'john');
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('should show empty message when search has no results', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} searchable />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      await user.type(searchInput, 'NonExistent');
      
      expect(screen.getByText('暂无数据')).toBeInTheDocument();
    });

    it('should clear search when input is cleared', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} searchable />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      await user.type(searchInput, 'John');
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      
      await user.clear(searchInput);
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    });
  });

  describe('Filter Functionality', () => {
    it('should filter data by column value', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} filterable />);
      
      const statusFilter = screen.getByText(/所有Status/).closest('select');
      if (statusFilter) {
        await user.selectOptions(statusFilter, 'Active');
      }
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
    });

    it('should reset to page 1 when filter changes', async () => {
      const user = userEvent.setup();
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} filterable />);
      
      // Go to page 2
      const nextButton = screen.getByTestId('chevron-right').closest('button');
      if (nextButton) await user.click(nextButton);
      
      // Apply filter
      const statusFilter = screen.getByText(/所有Status/).closest('select');
      if (statusFilter) {
        await user.selectOptions(statusFilter, 'Active');
      }
      
      expect(screen.getByText(/第 1 /)).toBeInTheDocument();
    });

    it('should allow multiple filters simultaneously', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} filterable />);
      
      const nameFilter = screen.getByText(/所有Name/).closest('select');
      const statusFilter = screen.getByText(/所有Status/).closest('select');
      
      if (nameFilter) await user.selectOptions(nameFilter, 'John Doe');
      if (statusFilter) await user.selectOptions(statusFilter, 'Active');
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
    });
  });

  describe('Sort Functionality', () => {
    it('should sort data in ascending order when column header is clicked', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} />);
      
      const ageHeader = screen.getByText('Age');
      await user.click(ageHeader);
      
      const rows = screen.getAllByRole('row').slice(1); // Skip header
      expect(rows[0]).toHaveTextContent('25');
    });

    it('should sort data in descending order when column header is clicked twice', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} />);
      
      const ageHeader = screen.getByText('Age');
      await user.click(ageHeader);
      await user.click(ageHeader);
      
      const rows = screen.getAllByRole('row').slice(1);
      expect(rows[0]).toHaveTextContent('40');
    });

    it('should show sort indicator', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} />);
      
      const ageHeader = screen.getByText('Age');
      await user.click(ageHeader);
      
      expect(screen.getByText('↑')).toBeInTheDocument();
    });

    it('should not sort non-sortable columns', () => {
      const nonSortableColumns = [
        { key: 'id' as const, label: 'ID' },
        { key: 'name' as const, label: 'Name' },
      ];
      render(<DataTable data={mockData} columns={nonSortableColumns} />);
      
      const nameHeader = screen.getByText('Name');
      expect(nameHeader).not.toHaveClass('cursor-pointer');
    });
  });

  describe('Pagination', () => {
    it('should display correct page information', () => {
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} />);
      
      expect(screen.getByText(/显示 1-5 \/ 15/)).toBeInTheDocument();
      expect(screen.getByText(/第 1 \/ 3 页/)).toBeInTheDocument();
    });

    it('should navigate to next page', async () => {
      const user = userEvent.setup();
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} />);
      
      const nextButton = screen.getByTestId('chevron-right').closest('button');
      if (nextButton) await user.click(nextButton);
      
      expect(screen.getByText(/第 2 \/ 3 页/)).toBeInTheDocument();
    });

    it('should navigate to previous page', async () => {
      const user = userEvent.setup();
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} />);
      
      const nextButton = screen.getByTestId('chevron-right').closest('button');
      if (nextButton) await user.click(nextButton);
      
      const prevButton = screen.getByTestId('chevron-left').closest('button');
      if (prevButton) await user.click(prevButton);
      
      expect(screen.getByText(/第 1 \/ 3 页/)).toBeInTheDocument();
    });

    it('should disable previous button on first page', () => {
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} />);
      
      const prevButton = screen.getByTestId('chevron-left').closest('button');
      expect(prevButton).toBeDisabled();
    });

    it('should disable next button on last page', async () => {
      const user = userEvent.setup();
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} />);
      
      const nextButton = screen.getByTestId('chevron-right').closest('button');
      if (nextButton) {
        await user.click(nextButton);
        await user.click(nextButton);
      }
      
      const finalNextButton = screen.getByTestId('chevron-right').closest('button');
      expect(finalNextButton).toBeDisabled();
    });

    it('should respect custom page size', () => {
      render(<DataTable data={mockData} columns={mockColumns} pageSize={2} />);
      
      expect(screen.getByText(/显示 1-2 \/ 5/)).toBeInTheDocument();
    });
  });

  describe('Row Click', () => {
    it('should call onRowClick when row is clicked', async () => {
      const handleRowClick = jest.fn();
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} onRowClick={handleRowClick} />);
      
      const firstRow = screen.getAllByRole('row')[1];
      await user.click(firstRow);
      
      expect(handleRowClick).toHaveBeenCalledWith(mockData[0]);
    });

    it('should not call onRowClick when not provided', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} />);
      
      const firstRow = screen.getAllByRole('row')[1];
      await user.click(firstRow);
      
      // Should not throw error
    });

    it('should add cursor-pointer class when onRowClick is provided', () => {
      render(<DataTable data={mockData} columns={mockColumns} onRowClick={() => {}} />);
      
      const firstRow = screen.getAllByRole('row')[1];
      expect(firstRow).toHaveClass('cursor-pointer');
    });
  });

  describe('Custom Render', () => {
    it('should use custom render function for column', () => {
      const customColumns = [
        { key: 'name' as const, label: 'Name', render: (value: any) => <span className="custom">{value}</span> },
      ];
      render(<DataTable data={mockData} columns={customColumns} />);
      
      expect(screen.getByText('John Doe')).toHaveClass('custom');
    });

    it('should pass row data to render function', () => {
      const customRender = jest.fn((value, row) => <span>{value}</span>);
      const customColumns = [
        { key: 'name' as const, label: 'Name', render: customRender },
      ];
      render(<DataTable data={mockData} columns={customColumns} />);
      
      expect(customRender).toHaveBeenCalledWith('John Doe', mockData[0]);
    });

    it('should display "-" for null/undefined values', () => {
      const dataWithNull = [{ id: 1, name: null as any, status: 'Active' }];
      const columns = [
        { key: 'name' as const, label: 'Name' },
      ];
      render(<DataTable data={dataWithNull} columns={columns} />);
      
      expect(screen.getByText('-')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty data array', () => {
      render(<DataTable data={[]} columns={mockColumns} />);
      expect(screen.getByText('暂无数据')).toBeInTheDocument();
    });

    it('should handle single row', () => {
      const singleRow = [mockData[0]];
      render(<DataTable data={singleRow} columns={mockColumns} />);
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('should handle large page size', () => {
      render(<DataTable data={mockData} columns={mockColumns} pageSize={100} />);
      expect(screen.queryByText(/第 1 /)).not.toBeInTheDocument();
    });

    it('should handle page size of 1', () => {
      render(<DataTable data={mockData} columns={mockColumns} pageSize={1} />);
      expect(screen.getByText(/显示 1-1 \/ 5/)).toBeInTheDocument();
    });

    it('should handle columns with no filterable columns', () => {
      const nonFilterableColumns = [
        { key: 'id' as const, label: 'ID' },
        { key: 'name' as const, label: 'Name' },
      ];
      render(<DataTable data={mockData} columns={nonFilterableColumns} filterable />);
      expect(screen.queryByText(/所有Name/)).not.toBeInTheDocument();
    });

    it('should handle special characters in search', async () => {
      const user = userEvent.setup();
      const dataWithSpecial = [{ id: 1, name: 'John@Doe', status: 'Active' }];
      const columns = [{ key: 'name' as const, label: 'Name' }];
      render(<DataTable data={dataWithSpecial} columns={columns} searchable />);
      
      const searchInput = screen.getByPlaceholderText('搜索...');
      await user.type(searchInput, '@');
      
      expect(screen.getByText('John@Doe')).toBeInTheDocument();
    });
  });

  describe('Integration Tests', () => {
    it('should handle search, filter, and sort together', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} searchable filterable />);
      
      // Search
      const searchInput = screen.getByPlaceholderText('搜索...');
      await user.type(searchInput, 'John');
      
      // Filter
      const statusFilter = screen.getByText(/所有Status/).closest('select');
      if (statusFilter) await user.selectOptions(statusFilter, 'Active');
      
      // Sort
      const ageHeader = screen.getByText('Age');
      await user.click(ageHeader);
      
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('should maintain state when switching pages with filters', async () => {
      const user = userEvent.setup();
      const largeData = [...mockData, ...mockData, ...mockData];
      render(<DataTable data={largeData} columns={mockColumns} pageSize={5} filterable />);
      
      // Apply filter
      const statusFilter = screen.getByText(/所有Status/).closest('select');
      if (statusFilter) await user.selectOptions(statusFilter, 'Active');
      
      // Navigate pages
      const nextButton = screen.getByTestId('chevron-right').closest('button');
      if (nextButton) await user.click(nextButton);
      
      // Filter should still be active
      expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper table structure', () => {
      render(<DataTable data={mockData} columns={mockColumns} />);
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByRole('columnheader')).toBeInTheDocument();
    });

    it('should support keyboard navigation for sortable headers', async () => {
      const user = userEvent.setup();
      render(<DataTable data={mockData} columns={mockColumns} />);
      
      const ageHeader = screen.getByText('Age');
      ageHeader.focus();
      await user.keyboard('{Enter}');
      
      expect(screen.getByText('↑')).toBeInTheDocument();
    });
  });
});
