import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';

describe('Table Components', () => {
  describe('Table', () => {
    it('should render table with children', () => {
      render(
        <Table>
          <tbody>
            <tr>
              <td>Test Content</td>
            </tr>
          </tbody>
        </Table>
      );
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <Table className="custom-class">
          <tbody>
            <tr>
              <td>Test</td>
            </tr>
          </tbody>
        </Table>
      );
      const table = screen.getByRole('table');
      expect(table).toHaveClass('custom-class');
    });

    it('should forward ref correctly', () => {
      const ref = React.createRef<HTMLTableElement>();
      render(
        <Table ref={ref}>
          <tbody>
            <tr>
              <td>Test</td>
            </tr>
          </tbody>
        </Table>
      );
      expect(ref.current).toBeInstanceOf(HTMLTableElement);
    });

    it('should wrap table in div with overflow-auto', () => {
      render(
        <Table>
          <tbody>
            <tr>
              <td>Test</td>
            </tr>
          </tbody>
        </Table>
      );
      const wrapper = screen.getByRole('table').parentElement;
      expect(wrapper).toHaveClass('relative');
      expect(wrapper).toHaveClass('w-full');
      expect(wrapper).toHaveClass('overflow-auto');
    });
  });

  describe('TableHeader', () => {
    it('should render thead element', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText('Header')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <Table>
          <TableHeader className="custom-class">
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );
      const thead = screen.getByRole('rowgroup');
      expect(thead).toHaveClass('custom-class');
    });

    it('should apply border-b style to rows', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );
      const thead = screen.getByRole('rowgroup');
      expect(thead).toHaveClass('[&_tr]:border-b');
    });
  });

  describe('TableBody', () => {
    it('should render tbody element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <Table>
          <TableBody className="custom-class">
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const tbody = document.querySelector('tbody');
      expect(tbody).toHaveClass('custom-class');
    });

    it('should remove border from last child row', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const tbody = document.querySelector('tbody');
      expect(tbody).toHaveClass('[&_tr:last-child]:border-0');
    });
  });

  describe('TableRow', () => {
    it('should render tr element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Row Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText('Row Content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <Table>
          <TableBody>
            <TableRow className="custom-class">
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const row = screen.getByRole('row');
      expect(row).toHaveClass('custom-class');
    });

    it('should handle onClick event', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();

      render(
        <Table>
          <TableBody>
            <TableRow onClick={handleClick}>
              <TableCell>Clickable Row</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const row = screen.getByRole('row');
      await user.click(row);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should apply hover styles', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const row = screen.getByRole('row');
      expect(row).toHaveClass('hover:bg-gray-50');
    });

    it('should apply border style', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const row = screen.getByRole('row');
      expect(row).toHaveClass('border-b');
    });
  });

  describe('TableHead', () => {
    it('should render th element', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Column Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );
      expect(screen.getByText('Column Header')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="custom-class">Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );
      const th = screen.getByRole('columnheader');
      expect(th).toHaveClass('custom-class');
    });

    it('should handle onClick event', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();

      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead onClick={handleClick}>Sortable Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );

      const th = screen.getByRole('columnheader');
      await user.click(th);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should have proper alignment and styling', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );
      const th = screen.getByRole('columnheader');
      expect(th).toHaveClass('text-left');
      expect(th).toHaveClass('align-middle');
      expect(th).toHaveClass('font-medium');
    });
  });

  describe('TableCell', () => {
    it('should render td element', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Cell Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText('Cell Content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell className="custom-class">Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const td = screen.getByRole('cell');
      expect(td).toHaveClass('custom-class');
    });

    it('should handle onClick event', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();

      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell onClick={handleClick}>Clickable Cell</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const td = screen.getByRole('cell');
      await user.click(td);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should have proper padding and alignment', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      const td = screen.getByRole('cell');
      expect(td).toHaveClass('p-4');
      expect(td).toHaveClass('align-middle');
    });
  });

  describe('Integration Tests', () => {
    it('should render complete table with all components', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Age</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>John</TableCell>
              <TableCell>25</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Jane</TableCell>
              <TableCell>30</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Age')).toBeInTheDocument();
      expect(screen.getByText('John')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();
      expect(screen.getByText('Jane')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });

    it('should handle row clicks in table body', async () => {
      const handleRowClick = jest.fn();
      const user = userEvent.setup();

      render(
        <Table>
          <TableBody>
            <TableRow onClick={handleRowClick}>
              <TableCell>Clickable</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );

      const row = screen.getByRole('row');
      await user.click(row);
      expect(handleRowClick).toHaveBeenCalledTimes(1);
    });

    it('should handle header clicks for sorting', async () => {
      const handleSort = jest.fn();
      const user = userEvent.setup();

      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead onClick={handleSort}>Sortable</TableHead>
            </TableRow>
          </TableHeader>
        </Table>
      );

      const th = screen.getByRole('columnheader');
      await user.click(th);
      expect(handleSort).toHaveBeenCalledTimes(1);
    });
  });

  describe('Edge Cases', () => {
    it('should render empty table', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Header</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody />
        </Table>
      );
      expect(screen.getByText('Header')).toBeInTheDocument();
    });

    it('should render table with multiple rows', () => {
      render(
        <Table>
          <TableBody>
            <TableRow><TableCell>Row 1</TableCell></TableRow>
            <TableRow><TableCell>Row 2</TableCell></TableRow>
            <TableRow><TableCell>Row 3</TableCell></TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText('Row 1')).toBeInTheDocument();
      expect(screen.getByText('Row 2')).toBeInTheDocument();
      expect(screen.getByText('Row 3')).toBeInTheDocument();
    });

    it('should render table with complex cell content', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>
                <div>
                  <span>Bold</span>
                  <em>Italic</em>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText('Bold')).toBeInTheDocument();
      expect(screen.getByText('Italic')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper table structure', () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Header</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Content</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByRole('columnheader')).toBeInTheDocument();
      expect(screen.getAllByRole('row')).toHaveLength(2);
      expect(screen.getByRole('cell')).toBeInTheDocument();
    });
  });
});
