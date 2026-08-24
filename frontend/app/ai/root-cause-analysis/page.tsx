'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RootCauseAnalysis {
  id: string;
  incident_id: string;
  root_cause: string;
  confidence: number;
  contributing_factors: string[];
  timeline: Array<{
    time: string;
    event: string;
  }>;
  recommended_actions: string[];
  created_at: string;
}

export default function RootCauseAnalysisPage() {
  const [analyses, setAnalyses] = useState<RootCauseAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [incidentId, setIncidentId] = useState('');
  const [selectedAnalysis, setSelectedAnalysis] = useState<RootCauseAnalysis | null>(null);

  useEffect(() => {
    fetchAnalyses();
  }, []);

  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/root-cause-analysis/analyses');
      setAnalyses(res.data.analyses || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载分析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!incidentId.trim()) return;
    try {
      const res = await api.post('/api/ai/root-cause-analysis/analyze', { incident_id: incidentId });
      setSelectedAnalysis(res.data);
      fetchAnalyses();
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
        <Button onClick={fetchAnalyses} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">根因分析</h1>
        <Button onClick={fetchAnalyses}>刷新</Button>
      </div>

      {/* 新建分析 */}
      <Card>
        <CardHeader>
          <CardTitle>创建根因分析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="输入事件ID..."
              value={incidentId}
              onChange={(e) => setIncidentId(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAnalyze()}
            />
            <Button onClick={handleAnalyze}>分析</Button>
          </div>
        </CardContent>
      </Card>

      {/* 分析结果 */}
      {selectedAnalysis && (
        <Card>
          <CardHeader>
            <CardTitle>分析结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">根因</h4>
                <p className="text-gray-700">{selectedAnalysis.root_cause}</p>
                <Badge variant="outline" className="mt-2">
                  置信度: {(selectedAnalysis.confidence * 100).toFixed(1)}%
                </Badge>
              </div>

              <div>
                <h4 className="font-semibold mb-2">贡献因素</h4>
                <ul className="list-disc list-inside space-y-1">
                  {selectedAnalysis.contributing_factors.map((factor, idx) => (
                    <li key={idx} className="text-gray-700">{factor}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="font-semibold mb-2">时间线</h4>
                <div className="space-y-2">
                  {selectedAnalysis.timeline.map((item, idx) => (
                    <div key={idx} className="flex gap-2 text-sm">
                      <span className="text-gray-500">{item.time}</span>
                      <span className="text-gray-700">{item.event}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold mb-2">推荐操作</h4>
                <ul className="list-disc list-inside space-y-1">
                  {selectedAnalysis.recommended_actions.map((action, idx) => (
                    <li key={idx} className="text-gray-700">{action}</li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 历史分析 */}
      <Card>
        <CardHeader>
          <CardTitle>历史分析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {analyses.map((analysis) => (
              <div
                key={analysis.id}
                className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => setSelectedAnalysis(analysis)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">事件: {analysis.incident_id}</h3>
                  <Badge variant="outline">
                    置信度: {(analysis.confidence * 100).toFixed(1)}%
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">{analysis.root_cause}</p>
                <div className="text-xs text-gray-500 mt-1">
                  创建于: {new Date(analysis.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
