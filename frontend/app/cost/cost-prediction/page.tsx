'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Prediction {
  service: string;
  current_cost: number;
  predicted_cost: number;
  confidence: number;
  time_horizon: string;
  factors: string[];
}

export default function CostPredictionPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeHorizon, setTimeHorizon] = useState('30d');

  const predict = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/cost/cost-prediction', { time_horizon: timeHorizon });
      setPredictions(res.data.predictions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '预测失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    predict();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">成本预测</h1>
        <div className="flex gap-2">
          <Input
            placeholder="时间范围 (如: 30d, 90d)"
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(e.target.value)}
            className="w-40"
          />
          <Button onClick={predict} disabled={loading}>
            {loading ? '预测中...' : '预测'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {predictions.map((pred, idx) => (
          <Card key={idx}>
            <CardHeader>
              <CardTitle>{pred.service}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">当前成本</div>
                    <div className="text-2xl font-bold">${pred.current_cost.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">预测成本</div>
                    <div className="text-2xl font-bold text-blue-600">${pred.predicted_cost.toFixed(2)}</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">置信度</div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-blue-500"
                      style={{ width: `${pred.confidence * 100}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{(pred.confidence * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-2">影响因素</div>
                  <div className="flex flex-wrap gap-1">
                    {pred.factors.map((factor) => (
                      <Badge key={factor} variant="outline" className="text-xs">{factor}</Badge>
                    ))}
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  时间范围: {pred.time_horizon}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
