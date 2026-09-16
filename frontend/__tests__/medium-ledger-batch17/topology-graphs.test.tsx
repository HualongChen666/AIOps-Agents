/**
 * Batch 17 regression — topology pages previously rendered a *static placeholder*
 * ("拓扑可视化区域" / "因果图可视化区域" / "拓扑可视化渲染区域") instead of drawing the
 * real graph returned by the backend. These tests pin the real behaviour:
 *   FE-111 app/topology/topology-view/page.tsx
 *   FE-114 app/topology/topology-visualization/page.tsx
 *   FE-117 app/topology/causal-graph/page.tsx
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as {
  get: jest.Mock;
  put: jest.Mock;
  post: jest.Mock;
};

// Capture the mock graph instances so we can assert on the drawn data.
const graphInstances: any[] = [];
jest.mock('@antv/g6', () => {
  const Graph = jest.fn().mockImplementation(() => {
    const instance = {
      changeData: jest.fn(),
      fitView: jest.fn(),
      updateLayout: jest.fn(),
      destroy: jest.fn(),
    };
    graphInstances.push(instance);
    return instance;
  });
  return { __esModule: true, default: { Graph }, Graph };
});

import TopologyViewPage from '@/app/topology/topology-view/page';
import TopologyVisualizationPage from '@/app/topology/topology-visualization/page';
import CausalGraphPage from '@/app/topology/causal-graph/page';

const graphNodes = [
  { id: 'agent', label: 'agent', pagerank: 0.3 },
  { id: 'host-1', label: 'host-1', pagerank: 0.2 },
];
const graphEdges = [{ source: 'agent', target: 'host-1', weight: 2 }];

describe('batch17 topology pages render real graphs', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    graphInstances.length = 0;
  });

  it('FE-111 topology-view draws the real graph from /api/topology/view', async () => {
    mockedApi.get.mockResolvedValue({
      data: { layout: 'tree', nodes: graphNodes, edges: graphEdges },
    });

    render(<TopologyViewPage />);

    await waitFor(() =>
      expect(mockedApi.get).toHaveBeenCalledWith('/api/topology/view?layout=tree'),
    );

    await waitFor(() => expect(graphInstances.length).toBeGreaterThan(0));
    const graph = graphInstances[0];
    expect(graph.changeData).toHaveBeenCalled();
    const drawn = graph.changeData.mock.calls[0][0];
    expect(drawn.nodes.map((n: any) => n.id)).toEqual(['agent', 'host-1']);
    expect(drawn.edges[0]).toMatchObject({ source: 'agent', target: 'host-1' });

    // summary reflects the real data, not fabricated zoom/filter text
    expect(screen.getAllByText(/2 节点 \/ 1 边/).length).toBeGreaterThan(0);
    expect(screen.queryByText('拓扑可视化区域')).not.toBeInTheDocument();
  });

  it('FE-114 topology-visualization draws the real graph and keeps real config', async () => {
    mockedApi.get.mockImplementation((url: string) => {
      if (url === '/api/topology/visualization') {
        return Promise.resolve({
          data: {
            id: 'default',
            name: 'Default',
            node_color: '#3b82f6',
            edge_color: '#94a3b8',
            show_labels: true,
            show_metrics: true,
            auto_refresh: false,
          },
        });
      }
      if (url === '/api/topology/topology-graph') {
        return Promise.resolve({
          data: { status: 'success', graph: { nodes: graphNodes, edges: graphEdges } },
        });
      }
      return Promise.reject(new Error(`unexpected url ${url}`));
    });

    render(<TopologyVisualizationPage />);

    await waitFor(() =>
      expect(mockedApi.get).toHaveBeenCalledWith('/api/topology/topology-graph'),
    );
    await waitFor(() => expect(graphInstances.length).toBeGreaterThan(0));
    const graph = graphInstances[0];
    expect(graph.changeData).toHaveBeenCalled();
    const drawn = graph.changeData.mock.calls[0][0];
    expect(drawn.nodes.map((n: any) => n.id)).toEqual(['agent', 'host-1']);

    expect(screen.getAllByText(/2 节点 \/ 1 边/).length).toBeGreaterThan(0);
    expect(screen.queryByText('拓扑可视化渲染区域')).not.toBeInTheDocument();
  });

  it('FE-117 causal-graph draws the real causal graph and shows real causal strength', async () => {
    mockedApi.get.mockResolvedValue({
      data: {
        nodes: [
          { id: 'a', name: 'svc-a', type: 'service' },
          { id: 'b', name: 'svc-b', type: 'service' },
        ],
        edges: [{ source: 'a', target: 'b', causal_strength: 0.8, type: 'depends' }],
        metrics: { total_nodes: 2, total_edges: 1, avg_causal_strength: 0.8 },
      },
    });

    render(<CausalGraphPage />);

    await waitFor(() =>
      expect(mockedApi.get).toHaveBeenCalledWith('/api/topology/causal-graph'),
    );
    await waitFor(() => expect(graphInstances.length).toBeGreaterThan(0));
    const graph = graphInstances[0];
    const drawn = graph.changeData.mock.calls[0][0];
    expect(drawn.nodes.map((n: any) => n.id)).toEqual(['a', 'b']);
    expect(drawn.edges[0]).toMatchObject({ source: 'a', target: 'b' });

    // real field is causal_strength (previously the page read `confidence` -> NaN)
    expect(screen.getByText(/因果强度: 80.0%/)).toBeInTheDocument();
    expect(screen.queryByText('因果图可视化区域')).not.toBeInTheDocument();
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
  });
});
