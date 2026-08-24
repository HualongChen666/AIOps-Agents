'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Prediction {
  event: string;
  predicted_effect: string;
  probability: number;
  time_horizon: string;
  confidence: number;
}

export default function CausalPredictionPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [event, setEvent] = useState('');
  const [timeHorizon, setTimeHorizon] = useState('1h');

  const predict = async () => {
    if (!event) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/topology/causal-prediction', {
        event,
        time_horizon: timeHorizon
      });
      setPredictions(res.data.predictions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '因果预测失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">因果预测</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>预测事件影响</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="输入事件"
              value={event}
              onChange={(e) => setEvent(e.target.value)}
            />
            <Input
              placeholder="时间范围 (如: 1h, 24h, 7d)"
              value={timeHorizon}
              onChange={(e) => setTimeHorizon(e.target.value)}
            />
          </div>
          <Button onClick={predict} disabled={loading} className="mt-4">
            {loading ? '预测中...' : '预测'}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {predictions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>预测结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {predictions.map((pred, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-semibold">{pred.event}</h3>
                      <div className="text-sm text-gray-500">时间范围: {pred.time_horizon}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">置信度: {(pred.confidence * 100).toFixed(1)}%</Badge>
                      <Badge variant="outline">概率: {(pred.probability * 100).toFixed(1)}%</Badge>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 mb-1">预测影响</div>
                    <div className="text-lg font-semibold">{pred.predicted_effect}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
