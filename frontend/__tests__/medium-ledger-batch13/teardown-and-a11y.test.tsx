import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Record every G6 graph instance created by the mocked constructor so the tests
// can assert that teardown actually happens.
jest.mock('@antv/g6', () => {
  const make = () => ({
    data: jest.fn(),
    render: jest.fn(),
    fitView: jest.fn(),
    on: jest.fn(),
    changeSize: jest.fn(),
    changeData: jest.fn(),
    destroy: jest.fn(),
  });
  const Graph = jest.fn(() => {
    const graph = make();
    (globalThis as any).__g6.push(graph);
    return graph;
  });
  return { __esModule: true, default: { Graph }, Graph };
});

jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as jest.Mocked<{
  get: jest.Mock;
}>;

import { RootCauseTopology } from '@/components/RootCauseTopology';
import { TopologyGraph } from '@/components/TopologyGraph';
import { ProgressBar, Tooltip } from '@/components/CommonUI';

const instances = () => (globalThis as any).__g6 as any[];

beforeEach(() => {
  (globalThis as any).__g6 = [];
  jest.clearAllMocks();
});

const renderWithQuery = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe('medium-ledger batch13 — teardown & a11y', () => {
  describe('FE-042 RootCauseTopology graph teardown', () => {
    it('destroys the graph instance on unmount', () => {
      const { unmount } = render(
        <RootCauseTopology nodes={[{ id: 'a', label: 'A' }]} edges={[]} />
      );
      const graph = instances()[0];
      expect(graph).toBeDefined();
      expect(graph.destroy).not.toHaveBeenCalled();

      unmount();

      expect(graph.destroy).toHaveBeenCalledTimes(1);
    });

    it('does not recreate the graph when only the data changes', () => {
      const { rerender } = render(
        <RootCauseTopology nodes={[{ id: 'a', label: 'A' }]} edges={[]} />
      );
      rerender(<RootCauseTopology nodes={[{ id: 'b', label: 'B' }]} edges={[]} />);

      // A single instance is reused; data is pushed onto it instead.
      expect(instances()).toHaveLength(1);
      expect(instances()[0].data).toHaveBeenCalledTimes(2);
    });

    it('reaches the latest onNodeClick through the stable listener', () => {
      const first = jest.fn();
      const second = jest.fn();
      const { rerender } = render(
        <RootCauseTopology nodes={[{ id: 'a', label: 'A' }]} edges={[]} onNodeClick={first} />
      );
      rerender(
        <RootCauseTopology nodes={[{ id: 'a', label: 'A' }]} edges={[]} onNodeClick={second} />
      );

      const handler = instances()[0].on.mock.calls.find((c: unknown[]) => c[0] === 'node:click')[1];
      handler({ item: { getID: () => 'a' } });

      expect(first).not.toHaveBeenCalled();
      expect(second).toHaveBeenCalledWith('a');
    });
  });

  describe('FE-054 TopologyGraph graph teardown', () => {
    it('destroys the graph instance on unmount', async () => {
      mockedApi.get.mockResolvedValue({
        data: { nodes: [{ id: 'n1', label: 'N1' }], edges: [] },
      });

      const { unmount } = renderWithQuery(<TopologyGraph />);
      await waitFor(() => expect(instances().length).toBeGreaterThan(0));

      const graph = instances()[0];
      unmount();

      expect(graph.destroy).toHaveBeenCalledTimes(1);
    });

    it('still binds data onto the created graph', async () => {
      mockedApi.get.mockResolvedValue({
        data: { nodes: [{ id: 'n1', label: 'N1' }], edges: [] },
      });

      renderWithQuery(<TopologyGraph />);
      await waitFor(() => expect(instances().length).toBeGreaterThan(0));

      expect(instances()[0].changeData).toHaveBeenCalled();
    });
  });

  describe('FE-040 ProgressBar with a zero max', () => {
    it('emits 0% (not NaN) for value 0 / max 0', () => {
      const { container } = render(<ProgressBar value={0} max={0} />);
      const fill = container.querySelector('.bg-blue-500') as HTMLElement;
      expect(fill.style.width).toBe('0%');
    });

    it('emits 0% (not Infinity) for a positive value with max 0', () => {
      const { container } = render(<ProgressBar value={50} max={0} />);
      const fill = container.querySelector('.bg-blue-500') as HTMLElement;
      expect(fill.style.width).toBe('0%');
    });

    it('still computes a normal percentage', () => {
      const { container } = render(<ProgressBar value={75} max={150} />);
      const fill = container.querySelector('.bg-blue-500') as HTMLElement;
      expect(fill.style.width).toBe('50%');
    });
  });

  describe('FE-040 Tooltip keyboard/focus support', () => {
    it('is focusable and reveals on focus / hides on blur', () => {
      const { container } = render(<Tooltip content="提示内容">触发器</Tooltip>);
      const wrapper = container.firstElementChild as HTMLElement;

      expect(wrapper).toHaveAttribute('tabindex', '0');
      expect(screen.queryByRole('tooltip')).toBeNull();

      fireEvent.focusIn(wrapper);
      expect(screen.getByRole('tooltip')).toHaveTextContent('提示内容');

      fireEvent.focusOut(wrapper);
      expect(screen.queryByRole('tooltip')).toBeNull();
    });

    it('links the trigger to the tooltip via aria-describedby while visible', () => {
      const { container } = render(<Tooltip content="提示内容">触发器</Tooltip>);
      const wrapper = container.firstElementChild as HTMLElement;

      fireEvent.focusIn(wrapper);
      const describedBy = wrapper.getAttribute('aria-describedby');
      expect(describedBy).toBeTruthy();
      expect(screen.getByRole('tooltip').id).toBe(describedBy);
    });
  });
});
