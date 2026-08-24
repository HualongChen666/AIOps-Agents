'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface LLMModel {
  id: string;
  name: string;
  provider: string;
  status: 'active' | 'inactive' | 'error';
  latency: number;
  cost_per_1k_tokens: number;
  capabilities: string[];
}

interface RoutingRule {
  id: string;
  name: string;
  condition: string;
  target_model: string;
  priority: number;
  enabled: boolean;
}

export default function LLMRouterPage() {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newRule, setNewRule] = useState({ name: '', condition: '', target_model: '', priority: 1 });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [modelsRes, rulesRes] = await Promise.all([
        api.get('/api/ai/llm-router/models'),
        api.get('/api/ai/llm-router/rules')
      ]);
      setModels(modelsRes.data.models || []);
      setRules(rulesRes.data.rules || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRule = async () => {
    try {
      await api.post('/api/ai/llm-router/rules', newRule);
      setNewRule({ name: '', condition: '', target_model: '', priority: 1 });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '添加规则失败');
    }
  };

  const handleToggleRule = async (id: string, enabled: boolean) => {
    try {
      await api.patch(`/api/ai/llm-router/rules/${id}`, { enabled: !enabled });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新规则失败');
    }
  };

  const handleDeleteRule = async (id: string) => {
    try {
      await api.delete(`/api/ai/llm-router/rules/${id}`);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除规则失败');
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
        <h1 className="text-3xl font-bold text-gray-900">LLM路由器</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 模型列表 */}
      <Card>
        <CardHeader>
          <CardTitle>可用模型</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div key={model.id} className="border rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{model.name}</h3>
                  <Badge variant={model.status === 'active' ? 'default' : 'secondary'}>
                    {model.status}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600">提供商: {model.provider}</div>
                <div className="text-sm text-gray-600">延迟: {model.latency}ms</div>
                <div className="text-sm text-gray-600">成本: ${model.cost_per_1k_tokens}/1K tokens</div>
                <div className="flex flex-wrap gap-1">
                  {model.capabilities.map((cap) => (
                    <Badge key={cap} variant="outline" className="text-xs">{cap}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 路由规则 */}
      <Card>
        <CardHeader>
          <CardTitle>路由规则</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {rules.map((rule) => (
              <div key={rule.id} className="border rounded-lg p-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{rule.name}</h3>
                    <Badge variant="outline">优先级: {rule.priority}</Badge>
                    <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                      {rule.enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                  <div className="text-sm text-gray-600 mt-1">条件: {rule.condition}</div>
                  <div className="text-sm text-gray-600">目标模型: {rule.target_model}</div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleRule(rule.id, rule.enabled)}
                  >
                    {rule.enabled ? '禁用' : '启用'}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteRule(rule.id)}
                  >
                    删除
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {/* 添加新规则 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">添加新规则</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="规则名称"
                value={newRule.name}
                onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
              />
              <Input
                placeholder="条件 (如: complexity > 0.8)"
                value={newRule.condition}
                onChange={(e) => setNewRule({ ...newRule, condition: e.target.value })}
              />
              <Input
                placeholder="目标模型ID"
                value={newRule.target_model}
                onChange={(e) => setNewRule({ ...newRule, target_model: e.target.value })}
              />
              <Input
                type="number"
                placeholder="优先级"
                value={newRule.priority}
                onChange={(e) => setNewRule({ ...newRule, priority: parseInt(e.target.value) || 1 })}
              />
            </div>
            <Button onClick={handleAddRule} className="mt-4">添加规则</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
