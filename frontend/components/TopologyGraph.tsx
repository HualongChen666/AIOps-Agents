'use client'

import React, { useEffect, useRef } from 'react';
import G6, { Graph } from '@antv/g6';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface TopologyNode {
  id: string;
  label: string;
  level?: number;
  status?: 'normal' | 'warning' | 'critical';
}

interface TopologyEdge {
  source: string;
  target: string;
  label?: string;
}

interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

const fetchTopology = async (): Promise<TopologyData> => {
  const res = await api.get('/api/v1/topologies');
  return res.data;
};

interface TopologyGraphProps {
  onNodeClick?: (nodeId: string) => void;
}

export const TopologyGraph: React.FC<TopologyGraphProps> = ({ onNodeClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  const { data, isLoading, error } = useQuery<TopologyData>(
    ['topology'],
    fetchTopology,
    {
      refetchInterval: 60_000, // 每分钟刷新一次
    }
  );

  useEffect(() => {
    if (!containerRef.current) return;
    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: containerRef.current.offsetHeight,
        fitView: true,
        defaultNode: {
          size: 30,
          style: {
            fill: '#1f4b99',
            stroke: '#fff',
            lineWidth: 2,
          },
          labelCfg: {
            style: { fill: '#fff', fontSize: 12 },
          },
        },
        defaultEdge: {
          style: { stroke: '#e2e2e2', lineWidth: 1 },
          labelCfg: { style: { fill: '#aaa', fontSize: 10 } },
        },
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
        },
      });
    }
    const graph = graphRef.current;
    if (data && graph) {
      const nodes = data.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        style: {
          fill:
            n.status === 'critical'
              ? '#ef4444'
              : n.status === 'warning'
              ? '#f59e0b'
              : '#1f4b99',
        },
      }));
      const edges = data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
      }));
      graph.changeData({ nodes, edges });
      graph.fitView();
    }
  }, [data]);

  if (isLoading) return <p className="text-gray-500 dark:text-gray-400">加载拓扑中…</p>;
  if (error)
    return (
      <p className="text-red-500">
        拓扑加载失败：{(error as Error).message}
      </p>
    );

  return (
    <div
      ref={containerRef}
      className="w-full h-[600px] bg-white dark:bg-gray-800 rounded shadow"
    ></div>
  );
};
