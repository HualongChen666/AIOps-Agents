import React from 'react';

interface TableProps {
  className?: string;
  children: React.ReactNode;
  colSpan?: number;
  rowSpan?: number;
}

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  ({ className = '', children, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table ref={ref} className={`w-full caption-bottom text-sm ${className}`} {...props}>
        {children}
      </table>
    </div>
  )
);

Table.displayName = 'Table';

export const TableHeader = React.forwardRef<HTMLTableSectionElement, TableProps>(
  ({ className = '', children, ...props }, ref) => (
    <thead ref={ref} className={`[&_tr]:border-b ${className}`} {...props}>
      {children}
    </thead>
  )
);

TableHeader.displayName = 'TableHeader';

export const TableBody = React.forwardRef<HTMLTableSectionElement, TableProps>(
  ({ className = '', children, ...props }, ref) => (
    <tbody ref={ref} className={`[&_tr:last-child]:border-0 ${className}`} {...props}>
      {children}
    </tbody>
  )
);

TableBody.displayName = 'TableBody';

export const TableRow = React.forwardRef<HTMLTableRowElement, TableProps>(
  ({ className = '', children, ...props }, ref) => (
    <tr ref={ref} className={`border-b border-gray-200 transition-colors hover:bg-gray-50 data-[state=selected]:bg-gray-100 ${className}`} {...props}>
      {children}
    </tr>
  )
);

TableRow.displayName = 'TableRow';

export const TableHead = React.forwardRef<HTMLTableCellElement, TableProps>(
  ({ className = '', children, ...props }, ref) => (
    <th ref={ref} className={`h-12 px-4 text-left align-middle font-medium text-gray-900 [&:has([role=checkbox])]:pr-0 ${className}`} {...props}>
      {children}
    </th>
  )
);

TableHead.displayName = 'TableHead';

export const TableCell = React.forwardRef<HTMLTableCellElement, TableProps>(
  ({ className = '', children, ...props }, ref) => (
    <td ref={ref} className={`p-4 align-middle [&:has([role=checkbox])]:pr-0 ${className}`} {...props}>
      {children}
    </td>
  )
);

TableCell.displayName = 'TableCell';
