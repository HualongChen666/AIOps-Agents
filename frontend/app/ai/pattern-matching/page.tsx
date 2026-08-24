'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Pattern {
  id: string;
  name: string;
  type: 'anomaly' | 'trend' | 'seasonal' | 'correlation';
  description: string;
  severity: 'low' | 'medium' | 'high';
  confidence: number;
  created_at: string;
}

interface MatchResult {
  pattern_id: string;
  pattern_name: string;
  matched_at: string;
  confidence: number;
  context: Record<string, any>;
}

export default function PatternMatchingPage() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newPattern, setNewPattern] = useState({
    name: '',
    type: 'anomaly' as const,
    description: '',
    severity: 'medium' as const
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [patternsRes, matchesRes] = await Promise.all([
        api.get('/api/ai/pattern-matching/patterns'),
        api.get('/api/ai/pattern-matching/matches')
      ]);
      setPatterns(patternsRes.data.patterns || []);
      setMatches(matchesRes.data.matches || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePattern = async () => {
    try {
      await api.post('/api/ai/pattern-matching/patterns', newPattern);
      setNewPattern({ name: '', type: 'anomaly', description: '', severity: 'medium' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建模式失败');
    }
  };

  const handleRunMatching = async () => {
    try {
      await api.post('/api/ai/pattern-matching/run');
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '运行匹配失败');
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
        <h1 className="text-3xl font-bold text-gray-900">模式匹配</h1>
        <div className="flex gap-2">
          <Button onClick={handleRunMatching}>运行匹配</Button>
          <Button onClick={fetchData}>刷新</Button>
        </div>
      </div>

      {/* 模式列表 */}
      <Card>
        <CardHeader>
          <CardTitle>模式列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {patterns.map((pattern) => (
              <div key={pattern.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{pattern.name}</h3>
                    <Badge variant="outline">{pattern.type}</Badge>
                    <Badge variant={
                      pattern.severity === 'high' ? 'destructive' :
                      pattern.severity === 'medium' ? 'secondary' : 'outline'
                    }>
                      {pattern.severity}
                    </Badge>
                  </div>
                  <Badge variant="outline">
                    置信度: {(pattern.confidence * 100).toFixed(1)}%
                  </Badge>
                </div>
                <p className="text-sm text-gray-600">{pattern.description}</p>
                <div className="text-xs text-gray-500 mt-1">
                  创建于: {new Date(pattern.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新模式 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建新模式</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="模式名称"
                value={newPattern.name}
                onChange={(e) => setNewPattern({ ...newPattern, name: e.target.value })}
              />
              <select
                className="border rounded px-3 py-2"
                value={newPattern.type}
                onChange={(e) => setNewPattern({ ...newPattern, type: e.target.value as any })}
              >
                <option value="anomaly">异常</option>
                <option value="trend">趋势</option>
                <option value="seasonal">季节性</option>
                <option value="correlation">相关性</option>
              </select>
              <select
                className="border rounded px-3 py-2"
                value={newPattern.severity}
                onChange={(e) => setNewPattern({ ...newPattern, severity: e.target.value as any })}
              >
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </div>
            <Input
              placeholder="描述"
              value={newPattern.description}
              onChange={(e) => setNewPattern({ ...newPattern, description: e.target.value })}
              className="mt-4"
            />
            <Button onClick={handleCreatePattern} className="mt-4">创建模式</Button>
          </div>
        </CardContent>
      </Card>

      {/* 匹配结果 */}
      <Card>
        <CardHeader>
          <CardTitle>匹配结果</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {matches.map((match, idx) => (
              <div key={idx} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h3 className="font-semibold">{match.pattern_name}</h3>
                    <Badge variant="outline">
                      置信度: {(match.confidence * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(match.matched_at).toLocaleString()}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  上下文: {JSON.stringify(match.context)}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
