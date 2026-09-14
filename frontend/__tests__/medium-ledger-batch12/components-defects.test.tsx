import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Provide the pieces NavBar/QuickActions need from next/navigation. `Link` is
// rendered as a plain anchor so class assertions work in jsdom.
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(() => '/'),
  useRouter: jest.fn(() => ({ push: jest.fn() })),
  Link: ({ children, href, className, ...props }: any) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  ),
}));

jest.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <button>Theme</button>,
}));

import { usePathname, useRouter } from 'next/navigation';
import { NavBar } from '@/components/NavBar';
import { QuickActions } from '@/components/QuickActions';
import { HistoryFilters } from '@/components/HistoryFilters';
import { ApprovalFilters } from '@/components/ApprovalFilters';
import { HealTimeline } from '@/components/charts/HealTimeline';
import { TrendChart } from '@/components/charts/TrendChart';
import { ResourceTrendChart } from '@/components/charts/ResourceTrendChart';

const noNaN = (calls: any[][]) => {
  expect(calls.length).toBeGreaterThan(0);
  for (const call of calls) {
    for (const arg of call) {
      if (typeof arg === 'number') {
        expect(Number.isNaN(arg)).toBe(false);
      }
    }
  }
};

describe('medium-ledger batch12 — component defects', () => {
  describe('FE-086 NavBar path matching', () => {
    it('does NOT mark /approval active for the /approvals prefix', () => {
      (usePathname as jest.Mock).mockReturnValue('/approvals');
      render(<NavBar />);
      expect(screen.getByText('审批')).not.toHaveClass('bg-primary');
    });

    it('marks /approval active on the exact route', () => {
      (usePathname as jest.Mock).mockReturnValue('/approval');
      render(<NavBar />);
      expect(screen.getByText('审批')).toHaveClass('bg-primary');
    });

    it('marks /approval active on a real sub-route', () => {
      (usePathname as jest.Mock).mockReturnValue('/approval/detail');
      render(<NavBar />);
      expect(screen.getByText('审批')).toHaveClass('bg-primary');
    });
  });

  describe('FE-083 QuickActions navigation error handling', () => {
    it('handles a rejected push promise without crashing', async () => {
      const push = jest.fn(() => Promise.reject(new Error('boom')));
      (useRouter as jest.Mock).mockReturnValue({ push });
      const user = userEvent.setup();
      render(<QuickActions />);

      await user.click(screen.getByText('新建告警规则'));
      await Promise.resolve();

      expect(push).toHaveBeenCalledWith('/alerts');
      expect(console.error).toHaveBeenCalledWith('Navigation failed:', expect.any(Error));
    });

    it('handles a synchronous throw from push without crashing', async () => {
      const push = jest.fn(() => {
        throw new Error('sync failure');
      });
      (useRouter as jest.Mock).mockReturnValue({ push });
      const user = userEvent.setup();
      render(<QuickActions />);

      await expect(user.click(screen.getByText('新建告警规则'))).resolves.toBeUndefined();
      expect(console.error).toHaveBeenCalledWith('Navigation failed:', expect.any(Error));
    });
  });

  describe('FE-056 HistoryFilters buttons', () => {
    it('reset restores defaults and notifies the parent', async () => {
      const onChange = jest.fn();
      const user = userEvent.setup();
      render(<HistoryFilters onFilterChange={onChange} />);

      await user.selectOptions(screen.getAllByRole('combobox')[0], 'alerts');
      onChange.mockClear();

      await user.click(screen.getByText('重置'));

      expect(onChange).toHaveBeenCalledWith({
        queryType: 'all',
        timeRange: '24h',
        severity: 'all',
        status: 'all',
      });
      expect(screen.getAllByRole('combobox')[0]).toHaveValue('all');
    });

    it('apply re-emits the current selection', async () => {
      const onChange = jest.fn();
      const user = userEvent.setup();
      render(<HistoryFilters onFilterChange={onChange} />);

      await user.selectOptions(screen.getAllByRole('combobox')[2], 'P0');
      onChange.mockClear();

      await user.click(screen.getByText('应用筛选'));

      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ severity: 'P0' }));
    });
  });

  describe('FE-063 ApprovalFilters buttons', () => {
    it('reset restores defaults and notifies the parent', async () => {
      const onChange = jest.fn();
      const user = userEvent.setup();
      render(<ApprovalFilters onFilterChange={onChange} />);

      await user.selectOptions(screen.getAllByRole('combobox')[0], 'approved');
      onChange.mockClear();

      await user.click(screen.getByText('重置'));

      expect(onChange).toHaveBeenCalledWith({
        status: 'pending',
        riskLevel: 'all',
        dateRange: '24h',
      });
      expect(screen.getAllByRole('combobox')[0]).toHaveValue('pending');
    });

    it('apply re-emits the current selection', async () => {
      const onChange = jest.fn();
      const user = userEvent.setup();
      render(<ApprovalFilters onFilterChange={onChange} />);

      await user.selectOptions(screen.getAllByRole('combobox')[1], 'high');
      onChange.mockClear();

      await user.click(screen.getByText('应用筛选'));

      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ riskLevel: 'high' }));
    });
  });

  describe('FE-059 HealTimeline detail panel', () => {
    const events = [
      {
        id: 'e1',
        timestamp: '2026-09-14T10:00:00.000Z',
        type: 'auto' as const,
        status: 'success' as const,
        alertId: 'AL-123',
        description: '重启服务',
      },
    ];

    it('renders real event fields instead of a placeholder sentence', () => {
      render(<HealTimeline events={events} />);
      fireEvent.click(screen.getByTestId('heal-event-card'));

      const detail = screen.getByTestId('heal-event-detail');
      expect(detail).toHaveTextContent('自动修复');
      expect(detail).toHaveTextContent('AL-123');
      expect(detail).toHaveTextContent('重启服务');
      expect(screen.queryByText(/操作的详细信息/)).toBeNull();
    });
  });

  describe('FE-053 / FE-057 single-point series do not produce NaN', () => {
    const collectCalls = (canvas: HTMLCanvasElement) => {
      const ctx: any = canvas.getContext('2d');
      return [...ctx.moveTo.mock.calls, ...ctx.lineTo.mock.calls, ...ctx.arc.mock.calls];
    };

    it('TrendChart guards the x-axis step for a single point', () => {
      render(<TrendChart data={[5]} />);
      const canvas = document.querySelector('canvas') as HTMLCanvasElement;
      noNaN(collectCalls(canvas));
    });

    it('ResourceTrendChart guards the x-axis step for a single point', () => {
      jest
        .spyOn(HTMLCanvasElement.prototype, 'getBoundingClientRect')
        .mockReturnValue({ width: 400, height: 200 } as DOMRect);
      render(
        <ResourceTrendChart data={[{ timestamp: 't0', cpu: 50, memory: 60, disk: 70 }]} />
      );
      const canvas = document.querySelector('canvas') as HTMLCanvasElement;
      noNaN(collectCalls(canvas));
    });
  });
});
