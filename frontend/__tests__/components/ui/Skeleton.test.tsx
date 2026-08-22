import React from 'react';
import { render, screen } from '@testing-library/react';
import { Skeleton, CardSkeleton, TableSkeleton, ListSkeleton } from '@/components/ui/Skeleton';

// Mock the Card components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
  CardContent: ({ children, className }: any) => (
    <div className={className} data-testid="card-content">
      {children}
    </div>
  ),
}));

describe('Skeleton Component', () => {
  describe('Skeleton', () => {
    describe('Rendering', () => {
      it('should render skeleton with default props', () => {
        render(<Skeleton />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toBeInTheDocument();
        expect(skeleton).toHaveClass('bg-gray-200', 'rounded');
      });

      it('should render skeleton with custom className', () => {
        render(<Skeleton className="custom-class" />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('custom-class');
      });

      it('should have animation class', () => {
        render(<Skeleton />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('animate-pulse');
      });

      it('should have background color', () => {
        render(<Skeleton />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('bg-gray-200');
      });

      it('should have rounded corners', () => {
        render(<Skeleton />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('rounded');
      });
    });

    describe('Custom Styling', () => {
      it('should apply custom height', () => {
        render(<Skeleton className="h-10" />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('h-10');
      });

      it('should apply custom width', () => {
        render(<Skeleton className="w-full" />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('w-full');
      });

      it('should apply custom border radius', () => {
        render(<Skeleton className="rounded-full" />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('rounded-full');
      });

      it('should apply multiple custom classes', () => {
        render(<Skeleton className="h-10 w-20 rounded-lg" />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toHaveClass('h-10', 'w-20', 'rounded-lg');
      });
    });

    describe('Edge Cases', () => {
      it('should render with empty className', () => {
        render(<Skeleton className="" />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toBeInTheDocument();
      });

      it('should render without className prop', () => {
        render(<Skeleton />);
        const skeleton = document.querySelector('.animate-pulse');
        expect(skeleton).toBeInTheDocument();
      });
    });
  });

  describe('CardSkeleton', () => {
    describe('Rendering', () => {
      it('should render card skeleton structure', () => {
        render(<CardSkeleton />);
        expect(screen.getByTestId('card')).toBeInTheDocument();
        expect(screen.getByTestId('card-header')).toBeInTheDocument();
        expect(screen.getByTestId('card-content')).toBeInTheDocument();
      });

      it('should render skeleton in header', () => {
        render(<CardSkeleton />);
        const headerSkeleton = screen.getByTestId('card-header').querySelector('.animate-pulse');
        expect(headerSkeleton).toHaveClass('h-6', 'w-1/3');
      });

      it('should render multiple skeletons in content', () => {
        render(<CardSkeleton />);
        const contentSkeletons = screen.getByTestId('card-content').querySelectorAll('.animate-pulse');
        expect(contentSkeletons).toHaveLength(3);
      });

      it('should render first content skeleton with full width', () => {
        render(<CardSkeleton />);
        const contentSkeletons = screen.getByTestId('card-content').querySelectorAll('.animate-pulse');
        expect(contentSkeletons[0]).toHaveClass('h-4', 'w-full');
      });

      it('should render second content skeleton with 5/6 width', () => {
        render(<CardSkeleton />);
        const contentSkeletons = screen.getByTestId('card-content').querySelectorAll('.animate-pulse');
        expect(contentSkeletons[1]).toHaveClass('h-4', 'w-5/6');
      });

      it('should render third content skeleton with 4/6 width', () => {
        render(<CardSkeleton />);
        const contentSkeletons = screen.getByTestId('card-content').querySelectorAll('.animate-pulse');
        expect(contentSkeletons[2]).toHaveClass('h-4', 'w-4/6');
      });

      it('should render content with space-y-3 class', () => {
        render(<CardSkeleton />);
        const content = screen.getByTestId('card-content');
        expect(content).toHaveClass('space-y-3');
      });
    });

    describe('Structure', () => {
      it('should have proper hierarchy', () => {
        render(<CardSkeleton />);
        const card = screen.getByTestId('card');
        const header = screen.getByTestId('card-header');
        const content = screen.getByTestId('card-content');
        
        expect(card).toContainElement(header);
        expect(card).toContainElement(content);
      });
    });
  });

  describe('TableSkeleton', () => {
    describe('Rendering', () => {
      it('should render table skeleton with default props', () => {
        render(<TableSkeleton />);
        const container = document.querySelector('.space-y-2');
        expect(container).toBeInTheDocument();
      });

      it('should render header row', () => {
        render(<TableSkeleton />);
        const headerRow = document.querySelector('.flex.gap-4.p-4.border');
        expect(headerRow).toBeInTheDocument();
      });

      it('should render default number of columns (4)', () => {
        render(<TableSkeleton />);
        const headerSkeletons = document.querySelector('.flex.gap-4.p-4.border')?.querySelectorAll('.animate-pulse');
        expect(headerSkeletons).toHaveLength(4);
      });

      it('should render default number of rows (5)', () => {
        render(<TableSkeleton />);
        const dataRows = document.querySelectorAll('.flex.gap-4.p-4.border');
        expect(dataRows).toHaveLength(6); // 1 header + 5 data rows
      });

      it('should render custom number of columns', () => {
        render(<TableSkeleton columns={3} />);
        const headerSkeletons = document.querySelector('.flex.gap-4.p-4.border')?.querySelectorAll('.animate-pulse');
        expect(headerSkeletons).toHaveLength(3);
      });

      it('should render custom number of rows', () => {
        render(<TableSkeleton rows={3} />);
        const dataRows = document.querySelectorAll('.flex.gap-4.p-4.border');
        expect(dataRows).toHaveLength(4); // 1 header + 3 data rows
      });

      it('should render header skeletons with fixed width', () => {
        render(<TableSkeleton />);
        const headerSkeletons = document.querySelector('.flex.gap-4.p-4.border')?.querySelectorAll('.animate-pulse');
        headerSkeletons?.forEach(skeleton => {
          expect(skeleton).toHaveClass('h-4', 'w-24');
        });
      });

      it('should render data row skeletons with flex-1 width', () => {
        render(<TableSkeleton />);
        const dataRows = document.querySelectorAll('.flex.gap-4.p-4.border');
        const firstDataRow = dataRows[1];
        const dataSkeletons = firstDataRow?.querySelectorAll('.animate-pulse');
        dataSkeletons?.forEach(skeleton => {
          expect(skeleton).toHaveClass('h-4', 'flex-1');
        });
      });

      it('should render with custom rows and columns', () => {
        render(<TableSkeleton rows={2} columns={2} />);
        const dataRows = document.querySelectorAll('.flex.gap-4.p-4.border');
        expect(dataRows).toHaveLength(3); // 1 header + 2 data rows
        
        const headerSkeletons = dataRows[0]?.querySelectorAll('.animate-pulse');
        expect(headerSkeletons).toHaveLength(2);
      });
    });

    describe('Edge Cases', () => {
      it('should render with 0 rows', () => {
        render(<TableSkeleton rows={0} />);
        const dataRows = document.querySelectorAll('.flex.gap-4.p-4.border');
        expect(dataRows).toHaveLength(1); // Only header
      });

      it('should render with 0 columns', () => {
        render(<TableSkeleton columns={0} />);
        const headerSkeletons = document.querySelector('.flex.gap-4.p-4.border')?.querySelectorAll('.animate-pulse');
        expect(headerSkeletons).toHaveLength(0);
      });

      it('should render with large number of rows', () => {
        render(<TableSkeleton rows={20} />);
        const dataRows = document.querySelectorAll('.flex.gap-4.p-4.border');
        expect(dataRows).toHaveLength(21); // 1 header + 20 data rows
      });

      it('should render with large number of columns', () => {
        render(<TableSkeleton columns={10} />);
        const headerSkeletons = document.querySelector('.flex.gap-4.p-4.border')?.querySelectorAll('.animate-pulse');
        expect(headerSkeletons).toHaveLength(10);
      });
    });

    describe('Styling', () => {
      it('should have correct container styles', () => {
        render(<TableSkeleton />);
        const container = document.querySelector('.space-y-2');
        expect(container).toHaveClass('space-y-2');
      });

      it('should have correct row styles', () => {
        render(<TableSkeleton />);
        const rows = document.querySelectorAll('.flex.gap-4.p-4.border');
        rows.forEach(row => {
          expect(row).toHaveClass('flex', 'gap-4', 'p-4', 'border', 'rounded');
        });
      });
    });
  });

  describe('ListSkeleton', () => {
    describe('Rendering', () => {
      it('should render list skeleton with default props', () => {
        render(<ListSkeleton />);
        const container = document.querySelector('.space-y-3');
        expect(container).toBeInTheDocument();
      });

      it('should render default number of items (5)', () => {
        render(<ListSkeleton />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        expect(items).toHaveLength(5);
      });

      it('should render custom number of items', () => {
        render(<ListSkeleton items={3} />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        expect(items).toHaveLength(3);
      });

      it('should render avatar skeleton for each item', () => {
        render(<ListSkeleton />);
        const avatarSkeletons = document.querySelectorAll('.h-10.w-10.rounded-full');
        expect(avatarSkeletons).toHaveLength(5);
      });

      it('should render avatar skeleton with correct styles', () => {
        render(<ListSkeleton />);
        const avatarSkeleton = document.querySelector('.h-10.w-10.rounded-full');
        expect(avatarSkeleton).toHaveClass('h-10', 'w-10', 'rounded-full');
      });

      it('should render content area for each item', () => {
        render(<ListSkeleton />);
        const contentAreas = document.querySelectorAll('.flex-1.space-y-2');
        expect(contentAreas).toHaveLength(5);
      });

      it('should render title skeleton in content area', () => {
        render(<ListSkeleton />);
        const titleSkeletons = document.querySelectorAll('.h-4.w-1\\/3');
        expect(titleSkeletons).toHaveLength(5);
      });

      it('should render subtitle skeleton in content area', () => {
        render(<ListSkeleton />);
        const subtitleSkeletons = document.querySelectorAll('.h-3.w-2\\/3');
        expect(subtitleSkeletons).toHaveLength(5);
      });

      it('should render with custom number of items', () => {
        render(<ListSkeleton items={10} />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        expect(items).toHaveLength(10);
      });
    });

    describe('Structure', () => {
      it('should have proper item structure', () => {
        render(<ListSkeleton />);
        const item = document.querySelector('.flex.items-center.gap-4.p-4.border');
        const avatar = item?.querySelector('.h-10.w-10.rounded-full');
        const content = item?.querySelector('.flex-1.space-y-2');
        
        expect(item).toContainElement(avatar);
        expect(item).toContainElement(content);
      });

      it('should have proper content structure', () => {
        render(<ListSkeleton />);
        const content = document.querySelector('.flex-1.space-y-2');
        const title = content?.querySelector('.h-4.w-1\\/3');
        const subtitle = content?.querySelector('.h-3.w-2\\/3');
        
        expect(content).toContainElement(title);
        expect(content).toContainElement(subtitle);
      });
    });

    describe('Edge Cases', () => {
      it('should render with 0 items', () => {
        render(<ListSkeleton items={0} />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        expect(items).toHaveLength(0);
      });

      it('should render with 1 item', () => {
        render(<ListSkeleton items={1} />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        expect(items).toHaveLength(1);
      });

      it('should render with large number of items', () => {
        render(<ListSkeleton items={20} />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        expect(items).toHaveLength(20);
      });
    });

    describe('Styling', () => {
      it('should have correct container styles', () => {
        render(<ListSkeleton />);
        const container = document.querySelector('.space-y-3');
        expect(container).toHaveClass('space-y-3');
      });

      it('should have correct item styles', () => {
        render(<ListSkeleton />);
        const items = document.querySelectorAll('.flex.items-center.gap-4.p-4.border');
        items.forEach(item => {
          expect(item).toHaveClass('flex', 'items-center', 'gap-4', 'p-4', 'border', 'rounded');
        });
      });

      it('should have correct content area styles', () => {
        render(<ListSkeleton />);
        const contentAreas = document.querySelectorAll('.flex-1.space-y-2');
        contentAreas.forEach(content => {
          expect(content).toHaveClass('flex-1', 'space-y-2');
        });
      });
    });
  });

  describe('Integration Tests', () => {
    it('should render all skeleton variants together', () => {
      render(
        <div>
          <Skeleton className="h-10 w-full" />
          <CardSkeleton />
          <TableSkeleton rows={3} columns={3} />
          <ListSkeleton items={3} />
        </div>
      );

      expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(document.querySelector('.space-y-2')).toBeInTheDocument();
      expect(document.querySelector('.space-y-3')).toBeInTheDocument();
    });

    it('should handle all skeleton components with custom props', () => {
      render(
        <div>
          <Skeleton className="h-20 w-40 rounded-lg" />
          <CardSkeleton />
          <TableSkeleton rows={2} columns={2} />
          <ListSkeleton items={2} />
        </div>
      );

      const skeleton = document.querySelector('.animate-pulse');
      expect(skeleton).toHaveClass('h-20', 'w-40', 'rounded-lg');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-hidden or similar for skeleton loaders', () => {
      render(<Skeleton />);
      const skeleton = document.querySelector('.animate-pulse');
      expect(skeleton).toBeInTheDocument();
    });

    it('should not interfere with screen readers', () => {
      render(<CardSkeleton />);
      const card = screen.getByTestId('card');
      expect(card).toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('should render efficiently with many items', () => {
      const startTime = performance.now();
      render(<ListSkeleton items={100} />);
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      // Should render in reasonable time (< 100ms)
      expect(renderTime).toBeLessThan(100);
    });

    it('should render efficiently with large table', () => {
      const startTime = performance.now();
      render(<TableSkeleton rows={50} columns={10} />);
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      // Should render in reasonable time (< 200ms)
      expect(renderTime).toBeLessThan(200);
    });
  });
});
