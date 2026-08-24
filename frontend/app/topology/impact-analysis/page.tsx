'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface ImpactResult {
  service: string;
  impact_level: 'critical' | 'high' | 'medium' | 'low';
  affected_services: string[];
  affected_users: number;
  estimated_downtime: number;
}

export default function ImpactAnalysisPage() {
  const [results, setResults] = useState<ImpactResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceId, setServiceId] = useState('');

  const analyzeImpact = async () => {
    if (!serviceId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/topology/impact-analysis', { service_id: serviceId });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '影响分析失败');
    } finally {
      setLoading(false);
    }
  };

  const getImpactColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">影响分析</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>分析服务影响</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="输入服务ID"
              value={serviceId}
              onChange={(e) => setServiceId(e.target.value)}
            />
            <Button onClick={analyzeImpact} disabled={loading}>
              {loading ? '分析中...' : '分析'}
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
            <CardTitle>分析结果</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {results.map((result, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">{result.service}</h3>
                    <Badge className={getImpactColor(result.impact_level)}>
                      {result.impact_level}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div>
                      <div className="text-sm text-gray-500">受影响服务数</div>
                      <div className="text-lg font-semibold">{result.affected_services.length}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">受影响用户</div>
                      <div className="text-lg font-semibold">{result.affected_users.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">预计停机时间</div>
                      <div className="text-lg font-semibold">{result.estimated_downtime}min</div>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 mb-2">受影响服务</div>
                    <div className="flex flex-wrap gap-1">
                      {result.affected_services.map((svc) => (
                        <Badge key={svc} variant="outline" className="text-xs">{svc}</Badge>
                      ))}
                    </div>
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
