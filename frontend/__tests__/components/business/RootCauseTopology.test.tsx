import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { RootCauseTopology } from '@/components/RootCauseTopology';

jest.mock('@antv/g6', () => {
  const create = () => ({
    data: jest.fn(),
    render: jest.fn(),
    fitView: jest.fn(),
    on: jest.fn(),
    changeSize: jest.fn(),
    destroy: jest.fn(),
  });
  const Graph = jest.fn(() => create());
  return { __esModule: true, default: { Graph }, Graph };
});

const g6 = jest.requireMock('@antv/g6') as { Graph: jest.Mock };
const GraphMock = g6.Graph;
const instance = () => GraphMock.mock.results[0]?.value;
const lastGraphData = () => instance().data.mock.calls[instance().data.mock.calls.length - 1][0] as {
  nodes: Array<{ id: string; style: { fill: string; stroke: string; lineWidth: number } }>;
  edges: Array<{ source: string; target: string; style: { stroke: string; lineWidth: number } }>;
};

const nodes = [
  { id: 'root', label: 'DB', is_root_cause: true },
  { id: 'alert', label: 'API', is_alert_source: true },
  { id: 'causal', label: 'Cache' },
  { id: 'u', label: 'U', health_status: 'unhealthy' },
  { id: 'd', label: 'D', health_status: 'degraded' },
  { id: 'h', label: 'H', health_status: 'healthy' },
  { id: 'plain', label: 'P' },
];

describe('RootCauseTopology', () => {
  beforeEach(() => {
    GraphMock.mockClear();
  });

  it('renders the legend', () => {
    render(<RootCauseTopology nodes={nodes} edges={[]} />);
    expect(screen.getByText('根因节点')).toBeInTheDocument();
    expect(screen.getByText('告警源')).toBeInTheDocument();
    expect(screen.getByText('因果路径')).toBeInTheDocument();
    expect(screen.getByText('健康')).toBeInTheDocument();
    expect(screen.getByText('降级')).toBeInTheDocument();
  });

  it('creates a single graph with the configured height and renders the data', () => {
    render(<RootCauseTopology nodes={nodes} edges={[]} height={420} />);

    expect(GraphMock).toHaveBeenCalledTimes(1);
    const cfg = GraphMock.mock.calls[0][0];
    expect(cfg.height).toBe(420);
    expect(cfg.container).toBeInstanceOf(HTMLElement);
    expect(instance().data).toHaveBeenCalled();
    expect(instance().render).toHaveBeenCalled();
    expect(instance().fitView).toHaveBeenCalled();
  });

  it('uses the default height of 500 when none is provided', () => {
    render(<RootCauseTopology nodes={nodes} edges={[]} />);
    expect(GraphMock.mock.calls[0][0].height).toBe(500);
  });

  it('styles nodes by root-cause / alert / causal-path / health', () => {
    render(<RootCauseTopology nodes={nodes} edges={[]} causalPath={['causal']} />);
    const byId = Object.fromEntries(lastGraphData().nodes.map((n) => [n.id, n.style]));

    expect(byId.root).toMatchObject({ fill: '#fee2e2', stroke: '#ef4444', lineWidth: 3 });
    expect(byId.alert).toMatchObject({ fill: '#fef3c7', stroke: '#f59e0b', lineWidth: 2 });
    expect(byId.causal).toMatchObject({ fill: '#dbeafe', stroke: '#3b82f6', lineWidth: 2 });
    expect(byId.u).toMatchObject({ fill: '#fee2e2', stroke: '#ef4444' });
    expect(byId.d).toMatchObject({ fill: '#fef3c7', stroke: '#f59e0b' });
    expect(byId.h).toMatchObject({ fill: '#dcfce7', stroke: '#22c55e' });
    expect(byId.plain).toMatchObject({ fill: '#f0f0f0', stroke: '#999' });
  });

  it('styles edges for explicit-causal, causal-path and default edges', () => {
    render(
      <RootCauseTopology
        nodes={nodes}
        edges={[
          { source: 'a', target: 'b', is_causal: true },
          { source: 'causal', target: 'causal2' },
          { source: 'x', target: 'y' },
        ]}
        causalPath={['causal', 'causal2']}
      />
    );
    const edges = lastGraphData().edges;
    expect(edges[0].style).toMatchObject({ stroke: '#3b82f6', lineWidth: 3 });
    expect(edges[1].style).toMatchObject({ stroke: '#3b82f6', lineWidth: 2 });
    expect(edges[2].style).toMatchObject({ stroke: '#ccc', lineWidth: 2 });
  });

  it('invokes onNodeClick with the clicked node id', () => {
    const onNodeClick = jest.fn();
    render(<RootCauseTopology nodes={nodes} edges={[]} onNodeClick={onNodeClick} />);

    const call = instance().on.mock.calls.find((c: unknown[]) => c[0] === 'node:click');
    expect(call).toBeDefined();
    act(() => {
      call[1]({ item: { getID: () => 'root' } });
    });

    expect(onNodeClick).toHaveBeenCalledWith('root');
  });

  it('does not throw on a node click when no handler is provided', () => {
    render(<RootCauseTopology nodes={nodes} edges={[]} />);
    const call = instance().on.mock.calls.find((c: unknown[]) => c[0] === 'node:click');
    expect(() => call[1]({ item: { getID: () => 'root' } })).not.toThrow();
  });

  it('resizes the graph on window resize', () => {
    render(<RootCauseTopology nodes={nodes} edges={[]} />);
    act(() => {
      window.dispatchEvent(new Event('resize'));
    });
    expect(instance().changeSize).toHaveBeenCalled();
    expect(instance().fitView).toHaveBeenCalled();
  });

  it('reuses the same graph instance when props change', () => {
    const { rerender } = render(<RootCauseTopology nodes={nodes} edges={[]} />);
    rerender(
      <RootCauseTopology
        nodes={[{ id: 'only', label: 'Only' }]}
        edges={[{ source: 'only', target: 'only' }]}
      />
    );
    expect(GraphMock).toHaveBeenCalledTimes(1);
    expect(instance().data).toHaveBeenCalledTimes(2);
  });
});
