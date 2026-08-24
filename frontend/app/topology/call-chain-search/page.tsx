'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface SearchCriteria {
  service?: string;
  min_duration?: number;
  max_duration?: number;
  status?: string;
  time_range?: string;
}

interface CallChainResult {
  trace_id: string;
  service: string;
  duration: number;
  status: string;
  timestamp: string;
}

export default function CallChainSearchPage() {
  const [results, setResults] = useState<CallChainResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [criteria, setCriteria] = useState<SearchCriteria>({});

  const handleSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/topology/call-chain-search', criteria);
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '搜索失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">调用链搜索</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>搜索条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Input
              placeholder="服务名称"
              value={criteria.service || ''}
              onChange={(e) => setCriteria({ ...criteria, service: e.target.value })}
            />
            <Input
              type="number"
              placeholder="最小持续时间(ms)"
              value={criteria.min_duration || ''}
              onChange={(e) => setCriteria({ ...criteria, min_duration: parseInt(e.target.value) || undefined })}
            />
            <Input
              type="number"
              placeholder="最大持续时间(ms)"
              value={criteria.max_duration || ''}
              onChange={(e) => setCriteria({ ...criteria, max_duration: parseInt(e.target.value) || undefined })}
            />
            <Input
              placeholder="状态"
              value={criteria.status || ''}
              onChange={(e) => setCriteria({ ...criteria, status: e.target.value })}
            />
          </div>
          <Button onClick={handleSearch} disabled={loading} className="mt-4">
            {loading ? '搜索中...' : '搜索'}
          </Button>
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
            <CardTitle>搜索结果 ({results.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {results.map((result, idx) => (
                <div key={idx} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="font-semibold">{result.trace_id}</div>
                    <div className="text-sm text-gray-500">{result.service} - {new Date(result.timestamp).toLocaleString()}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{result.duration}ms</Badge>
                    <Badge variant={result.status === 'success' ? 'default' : 'destructive'}>
                      {result.status}
                    </Badge>
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
