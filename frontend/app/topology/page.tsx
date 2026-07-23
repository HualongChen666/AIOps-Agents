'use client'

// P1 Enhancement: Import enhanced hooks and components
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { TopologyGraph } from '@/components/TopologyGraph';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface NodeDetail {
  id: string;
  name: string;
  type: string;
  status: 'normal' | 'warning' | 'critical';
  cpu: number;
  memory: number;
  latency: number;
  throughput: number;
  traffic: number;
  dependencyDepth: number;
}

interface TrafficFlow {
  source: string;
  target: string;
  requests: number;
  latency: number;
  errorRate: number;
}

interface HotPath {
  path: string[];
  latency: number;
  errorRate: number;
  throughput: number;
}

export default function TopologyPage() {
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [layoutMode, setLayoutMode] = useState<'force' | 'circular' | 'grid'>('force');
  const [showLabels, setShowLabels] = useState(true);

  const [showTraffic, setShowTraffic] = useState(true);
  const [showHotPaths, setShowHotPaths] = useState(false);

  // 🔧 修复: 使用真实 API 获取全链路拓扑数据
  const { data: topologyData, isLoading, error } = useQuery({
    queryKey: ['topology-full-link'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/topologies/full-link');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 修复: 从 API 数据转换流量流
  const [trafficFlows, setTrafficFlows] = useState<TrafficFlow[]>([
    { source: 'web-service', target: 'api-gateway', requests: 1200, latency: 45, errorRate: 0.5 },
    { source: 'api-gateway', target: 'auth-service', requests: 800, latency: 30, errorRate: 0.2 },
    { source: 'api-gateway', target: 'user-service', requests: 400, latency: 35, errorRate: 0.3 },
    { source: 'user-service', target: 'database', requests: 350, latency: 80, errorRate: 0.1 },
    { source: 'auth-service', target: 'cache', requests: 600, latency: 15, errorRate: 0.05 },
  ]);

  // 同步 API 数据到流量流
  useEffect(() => {
    if (topologyData && topologyData.edges) {
      const flows: TrafficFlow[] = topologyData.edges.map((edge: any) => ({
        source: edge.source,
        target: edge.target,
        requests: edge.requests || edge.traffic || 0,
        latency: edge.latency || 0,
        errorRate: edge.error_rate || edge.errorRate || 0,
      }));
      setTrafficFlows(flows);
    }
  }, [topologyData]);

  const [hotPaths, setHotPaths] = useState<HotPath[]>([
    {
      path: ['web-service', 'api-gateway', 'user-service', 'database'],
      latency: 160,
      errorRate: 0.4,
      throughput: 350,
    },
  ]);

  // 同步 API 数据到热点路径
  useEffect(() => {
    if (topologyData && topologyData.hot_paths) {
      const paths: HotPath[] = topologyData.hot_paths.map((path: any) => ({
        path: path.path || path.nodes || [],
        latency: path.latency || 0,
        errorRate: path.error_rate || path.errorRate || 0,
        throughput: path.throughput || 0,
      }));
      setHotPaths(paths);
    }
  }, [topologyData]);

  if (isLoading) return <div className="text-center text-gray-500">加载中...</div>;
  if (error) return <div className="text-center text-red-500">加载失败</div>;

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode({
      id: nodeId,
      name: `服务 ${nodeId}`,
      type: 'Service',
      status: 'normal',
      cpu: 45,
      memory: 60,
      latency: 120,
      throughput: 500,
      traffic: 1200,
      dependencyDepth: 3,
    });
  };

  const handleExport = (format: 'png' | 'json') => {
    if (format === 'png') {
      alert('导出为PNG图片');
    } else {
      alert('导出为JSON数据');
    }
  };

  return (
    <main className="p-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          全链路拓扑
        </h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowControls(!showControls)}>
            {showControls ? '隐藏控制栏' : '显示控制栏'}
          </Button>
          <Button variant={showTraffic ? 'default' : 'outline'} onClick={() => setShowTraffic(!showTraffic)}>
            流量可视化
          </Button>
          <Button variant={showHotPaths ? 'default' : 'outline'} onClick={() => setShowHotPaths(!showHotPaths)}>
            热点路径
          </Button>
          <Button variant="outline" onClick={() => handleExport('png')}>
            导出PNG
          </Button>
          <Button variant="outline" onClick={() => handleExport('json')}>
            导出JSON
          </Button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* 控制栏 */}
        {showControls && (
          <Card className="w-64">
            <CardHeader>
              <CardTitle className="text-sm">控制面板</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">布局模式</label>
                <Select value={layoutMode} onChange={(e) => setLayoutMode(e.target.value as any)}>
                  <option value="force">力导向</option>
                  <option value="circular">环形</option>
                  <option value="grid">网格</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">显示标签</label>
                <Button
                  variant={showLabels ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setShowLabels(!showLabels)}
                  className="w-full"
                >
                  {showLabels ? '显示' : '隐藏'}
                </Button>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">缩放</label>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    +
                  </Button>
                  <Button variant="outline" size="sm" className="flex-1">
                    -
                  </Button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">重置视图</label>
                <Button variant="outline" size="sm" className="w-full">
                  重置
                </Button>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">筛选</label>
                <Input placeholder="搜索节点..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">状态筛选</label>
                <Select>
                  <option value="">全部</option>
                  <option value="normal">正常</option>
                  <option value="warning">警告</option>
                  <option value="critical">严重</option>
                </Select>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 拓扑图 */}
        <div className="flex-1">
          <TopologyGraph onNodeClick={handleNodeClick} />
        </div>

        {/* 节点详情面板 */}
        {selectedNode && (
          <Card className="w-80">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">节点详情</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setSelectedNode(null)}>
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">节点ID</label>
                <p className="text-sm font-mono">{selectedNode.id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
                <p className="text-sm">{selectedNode.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                <p className="text-sm">{selectedNode.type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                <Badge className={selectedNode.status === 'normal' ? 'bg-green-100 text-green-800' : selectedNode.status === 'warning' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}>
                  {selectedNode.status === 'normal' ? '正常' : selectedNode.status === 'warning' ? '警告' : '严重'}
                </Badge>
              </div>
              <div className="pt-4 border-t">
                <h4 className="text-sm font-medium mb-3">实时指标</h4>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">CPU使用率</span>
                      <span className="font-medium">{selectedNode.cpu}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${selectedNode.cpu >= 80 ? 'bg-red-500' : selectedNode.cpu >= 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                        style={{ width: `${selectedNode.cpu}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">内存使用率</span>
                      <span className="font-medium">{selectedNode.memory}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${selectedNode.memory >= 80 ? 'bg-red-500' : selectedNode.memory >= 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                        style={{ width: `${selectedNode.memory}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">延迟</span>
                      <span className="font-medium">{selectedNode.latency}ms</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">吞吐量</span>
                      <span className="font-medium">{selectedNode.throughput} req/s</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">流量</span>
                      <span className="font-medium">{selectedNode.traffic} req/min</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-500">依赖深度</span>
                      <span className="font-medium">{selectedNode.dependencyDepth}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="pt-4 border-t">
                <Button variant="outline" size="sm" className="w-full mb-2">
                  查看详情
                </Button>
                <Button variant="outline" size="sm" className="w-full">
                  查看日志
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 流量可视化面板 */}
        {showTraffic && (
          <Card className="w-80">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">流量可视化</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowTraffic(false)}>
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {trafficFlows.map((flow, index) => (
                  <div key={index} className="p-3 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{flow.source} → {flow.target}</span>
                      <span className="text-xs text-gray-500">{flow.requests} req/s</span>
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">延迟</span>
                        <span>{flow.latency}ms</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">错误率</span>
                        <span className={flow.errorRate > 0.5 ? 'text-red-600' : 'text-green-600'}>{(flow.errorRate * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 热点路径面板 */}
        {showHotPaths && (
          <Card className="w-80">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">热点路径</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowHotPaths(false)}>
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {hotPaths.map((path, index) => (
                  <div key={index} className="p-3 border border-orange-200 bg-orange-50 rounded-lg">
                    <div className="flex items-center gap-1 mb-2 text-sm">
                      {path.path.map((node, i) => (
                        <span key={i}>
                          {node}
                          {i < path.path.length - 1 && <span className="text-gray-400 mx-1">→</span>}
                        </span>
                      ))}
                    </div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">总延迟</span>
                        <span className="font-medium">{path.latency}ms</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">错误率</span>
                        <span className="font-medium text-orange-600">{(path.errorRate * 100).toFixed(2)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">吞吐量</span>
                        <span className="font-medium">{path.throughput} req/s</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
