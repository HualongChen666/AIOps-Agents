'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface NodeType {
  id: string;
  name: string;
  type: 'llm' | 'tool' | 'condition' | 'action' | 'input' | 'output';
  description: string;
  config_schema: Record<string, any>;
  examples: string[];
}

interface NodeInstance {
  id: string;
  node_type_id: string;
  node_type_name: string;
  workflow_id: string;
  config: Record<string, any>;
  position: { x: number; y: number };
}

export default function LangGraphNodesPage() {
  const [nodeTypes, setNodeTypes] = useState<NodeType[]>([]);
  const [instances, setInstances] = useState<NodeInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [newInstance, setNewInstance] = useState({
    node_type_id: '',
    workflow_id: '',
    config: '{}'
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [typesRes, instancesRes] = await Promise.all([
        api.get('/api/ai/langgraph-nodes/types'),
        api.get('/api/ai/langgraph-nodes/instances')
      ]);
      setNodeTypes(typesRes.data.types || []);
      setInstances(instancesRes.data.instances || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInstance = async () => {
    try {
      const config = JSON.parse(newInstance.config);
      await api.post('/api/ai/langgraph-nodes/instances', {
        ...newInstance,
        config
      });
      setNewInstance({ node_type_id: '', workflow_id: '', config: '{}' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建实例失败');
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
        <h1 className="text-3xl font-bold text-gray-900">节点类型</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 节点类型 */}
      <Card>
        <CardHeader>
          <CardTitle>节点类型</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nodeTypes.map((type) => (
              <div
                key={type.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedType === type.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedType(type.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{type.name}</h3>
                  <Badge variant="outline">{type.type}</Badge>
                </div>
                <p className="text-sm text-gray-600 mb-2">{type.description}</p>
                <div className="text-xs text-gray-500">
                  配置项: {Object.keys(type.config_schema).length}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 节点类型详情 */}
      {selectedType && (
        <Card>
          <CardHeader>
            <CardTitle>节点类型详情</CardTitle>
          </CardHeader>
          <CardContent>
            {nodeTypes.find(t => t.id === selectedType) && (
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">配置Schema</h4>
                  <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
                    {JSON.stringify(nodeTypes.find(t => t.id === selectedType)?.config_schema, null, 2)}
                  </pre>
                </div>
                {nodeTypes.find(t => t.id === selectedType)?.examples && (
                  <div>
                    <h4 className="font-semibold mb-2">示例</h4>
                    <div className="space-y-2">
                      {nodeTypes.find(t => t.id === selectedType)?.examples.map((example, idx) => (
                    <div key={idx} className="bg-gray-100 p-2 rounded text-sm">
                      {example}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )}

      {/* 节点实例 */}
      <Card>
        <CardHeader>
          <CardTitle>节点实例</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {instances.map((instance) => (
              <div key={instance.id} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold">{instance.node_type_name}</h3>
                  <Badge variant="outline">工作流: {instance.workflow_id}</Badge>
                </div>
                <div className="text-xs text-gray-500">
                  配置: {JSON.stringify(instance.config)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  位置: ({instance.position.x}, {instance.position.y})
                </div>
              </div>
            ))}
          </div>

          {/* 创建新实例 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建节点实例</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="节点类型ID"
                value={newInstance.node_type_id}
                onChange={(e) => setNewInstance({ ...newInstance, node_type_id: e.target.value })}
              />
              <Input
                placeholder="工作流ID"
                value={newInstance.workflow_id}
                onChange={(e) => setNewInstance({ ...newInstance, workflow_id: e.target.value })}
              />
            </div>
            <textarea
              placeholder="配置 (JSON格式)"
              value={newInstance.config}
              onChange={(e) => setNewInstance({ ...newInstance, config: e.target.value })}
              className="w-full border rounded p-2 h-24 mt-4 font-mono text-sm"
            />
            <Button onClick={handleCreateInstance} className="mt-4">创建实例</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
