'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface DSLDefinition {
  id: string;
  name: string;
  version: string;
  description: string;
  content: string;
  status: 'draft' | 'published' | 'deprecated';
  created_at: string;
  updated_at: string;
}

interface DSLSchema {
  node_types: string[];
  edge_types: string[];
  properties: Record<string, any>;
}

export default function LangGraphDSLPage() {
  const [definitions, setDefinitions] = useState<DSLDefinition[]>([]);
  const [schema, setSchema] = useState<DSLSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDefinition, setSelectedDefinition] = useState<DSLDefinition | null>(null);
  const [newDefinition, setNewDefinition] = useState({
    name: '',
    version: '1.0.0',
    description: '',
    content: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [defsRes, schemaRes] = await Promise.all([
        api.get('/api/ai/langgraph-dsl/definitions'),
        api.get('/api/ai/langgraph-dsl/schema')
      ]);
      setDefinitions(defsRes.data.definitions || []);
      setSchema(schemaRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDefinition = async () => {
    try {
      await api.post('/api/ai/langgraph-dsl/definitions', newDefinition);
      setNewDefinition({ name: '', version: '1.0.0', description: '', content: '' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建定义失败');
    }
  };

  const handlePublishDefinition = async (id: string) => {
    try {
      await api.patch(`/api/ai/langgraph-dsl/definitions/${id}`, { status: 'published' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '发布定义失败');
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
        <h1 className="text-3xl font-bold text-gray-900">DSL语言定义</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* DSL Schema */}
      {schema && (
        <Card>
          <CardHeader>
            <CardTitle>DSL Schema</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-semibold mb-2">节点类型</h4>
                <div className="flex flex-wrap gap-1">
                  {schema.node_types.map((type) => (
                    <Badge key={type} variant="outline">{type}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="font-semibold mb-2">边类型</h4>
                <div className="flex flex-wrap gap-1">
                  {schema.edge_types.map((type) => (
                    <Badge key={type} variant="outline">{type}</Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* DSL定义列表 */}
      <Card>
        <CardHeader>
          <CardTitle>DSL定义</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {definitions.map((def) => (
              <div
                key={def.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedDefinition?.id === def.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedDefinition(def)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{def.name}</h3>
                    <Badge variant="outline">{def.version}</Badge>
                    <Badge variant={
                      def.status === 'published' ? 'default' :
                      def.status === 'deprecated' ? 'destructive' : 'secondary'
                    }>
                      {def.status}
                    </Badge>
                  </div>
                  {def.status === 'draft' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePublishDefinition(def.id);
                      }}
                    >
                      发布
                    </Button>
                  )}
                </div>
                <p className="text-sm text-gray-600">{def.description}</p>
                <div className="text-xs text-gray-500 mt-1">
                  更新于: {new Date(def.updated_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新定义 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建DSL定义</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="定义名称"
                value={newDefinition.name}
                onChange={(e) => setNewDefinition({ ...newDefinition, name: e.target.value })}
              />
              <Input
                placeholder="版本"
                value={newDefinition.version}
                onChange={(e) => setNewDefinition({ ...newDefinition, version: e.target.value })}
              />
              <Input
                placeholder="描述"
                value={newDefinition.description}
                onChange={(e) => setNewDefinition({ ...newDefinition, description: e.target.value })}
                className="md:col-span-2"
              />
            </div>
            <textarea
              placeholder="DSL内容..."
              value={newDefinition.content}
              onChange={(e) => setNewDefinition({ ...newDefinition, content: e.target.value })}
              className="w-full border rounded p-2 h-32 mt-4 font-mono text-sm"
            />
            <Button onClick={handleCreateDefinition} className="mt-4">创建定义</Button>
          </div>
        </CardContent>
      </Card>

      {/* 定义详情 */}
      {selectedDefinition && (
        <Card>
          <CardHeader>
            <CardTitle>定义详情</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm">
              {selectedDefinition.content}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
