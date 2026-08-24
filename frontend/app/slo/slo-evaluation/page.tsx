'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface EvaluationResult {
  slo_id: string;
  slo_name: string;
  period_start: string;
  period_end: string;
  compliance: number;
  target: number;
  status: 'pass' | 'fail';
  incidents: number;
  total_downtime: number;
}

export default function SLOEvaluationPage() {
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState('30d');

  const evaluate = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/slo/evaluation', { period });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '评估失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    evaluate();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO评估</h1>
        <div className="flex gap-2">
          <Input
            placeholder="评估周期 (如: 30d, 7d, 24h)"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="w-40"
          />
          <Button onClick={evaluate} disabled={loading}>
            {loading ? '评估中...' : '评估'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.map((result) => (
          <Card key={result.slo_id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{result.slo_name}</CardTitle>
                <Badge variant={result.status === 'pass' ? 'default' : 'destructive'}>
                  {result.status === 'pass' ? '通过' : '未通过'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">合规率</span>
                    <span className="font-semibold">{result.compliance.toFixed(2)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${result.status === 'pass' ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${result.compliance}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">目标: {result.target}%</div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">事件数</div>
                    <div className="text-lg font-semibold">{result.incidents}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">停机时间</div>
                    <div className="text-lg font-semibold">{result.total_downtime}min</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">周期</div>
                    <div className="text-sm">{new Date(result.period_start).toLocaleDateString()} - {new Date(result.period_end).toLocaleDateString()}</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
