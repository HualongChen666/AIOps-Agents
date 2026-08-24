'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface InferenceResult {
  cause: string;
  effect: string;
  probability: number;
  evidence: string[];
  confidence: 'high' | 'medium' | 'low';
}

export default function CausalInferencePage() {
  const [results, setResults] = useState<InferenceResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [event, setEvent] = useState('');

  const runInference = async () => {
    if (!event) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/topology/causal-inference', { event });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '因果推断失败');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">因果推断</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>输入事件进行推断</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="输入事件描述"
              value={event}
              onChange={(e) => setEvent(e.target.value)}
            />
            <Button onClick={runInference} disabled={loading}>
              {loading ? '推断中...' : '推断'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>推断结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {results.map((result, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{result.cause}</span>
                      <span className="text-gray-400">→</span>
                      <span className="font-semibold">{result.effect}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={getConfidenceColor(result.confidence)}>
                        {result.confidence}
                      </Badge>
                      <Badge variant="secondary">概率: {(result.probability * 100).toFixed(1)}%</Badge>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 mb-2">证据</div>
                    <ul className="text-sm text-gray-600 list-disc list-inside">
                      {result.evidence.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
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
