'use client'

import React, { useEffect, useRef } from 'react';
import G6, { Graph } from '@antv/g6';
import { Network, AlertTriangle, CheckCircle } from 'lucide-react';

interface TopologyNode {
  id: string;
  label: string;
  layer?: string;
  health_status?: string;
  is_root_cause?: boolean;
  is_alert_source?: boolean;
}

interface TopologyEdge {
  source: string;
  target: string;
  label?: string;
  is_causal?: boolean;
}

interface RootCauseTopologyProps {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  causalPath?: string[];
  onNodeClick?: (nodeId: string) => void;
  height?: number;
}

export const RootCauseTopology: React.FC<RootCauseTopologyProps> = ({
  nodes,
  edges,
  causalPath = [],
  onNodeClick,
  height = 500,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // 初始化图表
    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: height,
        fitView: true,
        fitViewPadding: 20,
        layout: {
          type: 'dagre',
          rankdir: 'LR',
          nodesep: 50,
          ranksep: 100,
        },
        defaultNode: {
          size: [120, 40],
          type: 'rect',
          style: {
            fill: '#f0f0f0',
            stroke: '#999',
            lineWidth: 1,
            radius: 4,
          },
          labelCfg: {
            style: {
              fill: '#333',
              fontSize: 12,
            },
            position: 'center',
          },
        },
        defaultEdge: {
          type: 'cubic-horizontal',
          style: {
            stroke: '#ccc',
            lineWidth: 2,
          },
          labelCfg: {
            style: {
              fill: '#666',
              fontSize: 10,
            },
            refY: 5,
          },
        },
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
        },
      });
    }

    const graph = graphRef.current;

    // 处理节点数据
    const processedNodes = nodes.map((node) => {
      let fill = '#f0f0f0';
      let stroke = '#999';
      let lineWidth = 1;

      // 根因节点 - 红色
      if (node.is_root_cause) {
        fill = '#fee2e2';
        stroke = '#ef4444';
        lineWidth = 3;
      }
      // 告警源节点 - 橙色
      else if (node.is_alert_source) {
        fill = '#fef3c7';
        stroke = '#f59e0b';
        lineWidth = 2;
      }
      // 因果路径上的节点 - 蓝色
      else if (causalPath.includes(node.id)) {
        fill = '#dbeafe';
        stroke = '#3b82f6';
        lineWidth = 2;
      }
      // 健康状态着色
      else if (node.health_status === 'unhealthy') {
        fill = '#fee2e2';
        stroke = '#ef4444';
      } else if (node.health_status === 'degraded') {
        fill = '#fef3c7';
        stroke = '#f59e0b';
      } else if (node.health_status === 'healthy') {
        fill = '#dcfce7';
        stroke = '#22c55e';
      }

      return {
        id: node.id,
        label: node.label,
        style: {
          fill,
          stroke,
          lineWidth,
        },
      };
    });

    // 处理边数据
    const processedEdges = edges.map((edge) => {
      let stroke = '#ccc';
      let lineWidth = 2;
      let lineDash: number[] | undefined = undefined;

      // 因果路径上的边 - 蓝色实线
      if (edge.is_causal) {
        stroke = '#3b82f6';
        lineWidth = 3;
      }
      // 检查边是否在因果路径上
      else if (
        causalPath.includes(edge.source) &&
        causalPath.includes(edge.target) &&
        Math.abs(causalPath.indexOf(edge.source) - causalPath.indexOf(edge.target)) === 1
      ) {
        stroke = '#3b82f6';
        lineWidth = 2;
      }

      return {
        source: edge.source,
        target: edge.target,
        label: edge.label,
        style: {
          stroke,
          lineWidth,
          lineDash,
        },
      };
    });

    // 更新图表数据
    graph.data({
      nodes: processedNodes,
      edges: processedEdges,
    });

    graph.render();
    graph.fitView();

    // 添加节点点击事件
    graph.on('node:click', (evt) => {
      const nodeId = evt.item?.getID();
      if (nodeId && onNodeClick) {
        onNodeClick(nodeId);
      }
    });

    // 清理函数
    return () => {
      // graph.destroy() 会在组件卸载时调用
    };
  }, [nodes, edges, causalPath, onNodeClick, height]);

  // 响应式调整
  useEffect(() => {
    const handleResize = () => {
      if (graphRef.current && containerRef.current) {
        graphRef.current.changeSize(
          containerRef.current.offsetWidth,
          height
        );
        graphRef.current.fitView();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-100 border-2 border-red-500 rounded"></div>
          <span>根因节点</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-100 border-2 border-orange-500 rounded"></div>
          <span>告警源</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-100 border-2 border-blue-500 rounded"></div>
          <span>因果路径</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-100 border-2 border-green-500 rounded"></div>
          <span>健康</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-100 border-2 border-yellow-500 rounded"></div>
          <span>降级</span>
        </div>
      </div>
      <div
        ref={containerRef}
        className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-md border"
        style={{ height: `${height}px` }}
      />
    </div>
  );
};

export default RootCauseTopology;
