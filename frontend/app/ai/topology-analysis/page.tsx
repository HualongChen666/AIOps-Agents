'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface TopologyNode {
  id: string;
  name: string;
  type: 'service' | 'database' | 'cache' | 'queue' | 'external';
  status: 'healthy' | 'degraded' | 'down';
  dependencies: string[];
}

interface TopologyAnalysis {
  id: string;
  timestamp: string;
  critical_path: string[];
  bottleneck_nodes: string[];
  risk_score: number;
  recommendations: string[];
}

export default function TopologyAnalysisPage() {
  const [nodes, setNodes] = useState<TopologyNode[]>([]);
  const [analyses, setAnalyses] = useState<TopologyAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [nodesRes, analysesRes] = await Promise.all([
        api.get('/api/ai/topology-analysis/nodes'),
        api.get('/api/ai/topology-analysis/analyses')
      ]);
      setNodes(nodesRes.data.nodes || []);
      setAnalyses(analysesRes.data.analyses || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    try {
      await api.post('/api/ai/topology-analysis/analyze');
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '分析失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑分析</h1>
        <div className="flex gap-2">
          <Button onClick={handleRunAnalysis}>运行分析</Button>
          <Button onClick={fetchData}>刷新</Button>
        </div>
      </div>

      {/* 拓扑节点 */}
      <Card>
        <CardHeader>
          <CardTitle>拓扑节点</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nodes.map((node) => (
              <div key={node.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{node.name}</h3>
                  <Badge variant={
                    node.status === 'healthy' ? 'default' :
                    node.status === 'degraded' ? 'secondary' : 'destructive'
                  }>
                    {node.status}
                  </Badge>
                </div>
                <Badge variant="outline" className="mb-2">{node.type}</Badge>
                <div className="text-sm text-gray-600">
                  依赖: {node.dependencies.length > 0 ? node.dependencies.join(', ') : '无'}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 分析结果 */}
      <Card>
        <CardHeader>
          <CardTitle>分析结果</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {analyses.map((analysis) => (
              <div key={analysis.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="outline">
                    风险分数: {analysis.risk_score.toFixed(2)}
                  </Badge>
                  <span className="text-sm text-gray-500">
                    {new Date(analysis.timestamp).toLocaleString()}
                  </span>
                </div>

                <div className="mb-3">
                  <h4 className="font-semibold text-sm mb-1">关键路径</h4>
                  <div className="flex flex-wrap gap-1">
                    {analysis.critical_path.map((node, idx) => (
                      <Badge key={idx} variant="outline">{node}</Badge>
                    ))}
                  </div>
                </div>

                <div className="mb-3">
                  <h4 className="font-semibold text-sm mb-1">瓶颈节点</h4>
                  <div className="flex flex-wrap gap-1">
                    {analysis.bottleneck_nodes.map((node, idx) => (
                      <Badge key={idx} variant="destructive">{node}</Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-sm mb-1">推荐操作</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {analysis.recommendations.map((rec, idx) => (
                      <li key={idx} className="text-gray-700">{rec}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
