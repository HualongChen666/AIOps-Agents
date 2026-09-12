'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

export interface EndpointSpec {
  label: string;
  method?: 'get' | 'post';
  path: string;
  params?: Record<string, unknown>;
  body?: Record<string, unknown>;
}

interface EndpointPanelProps {
  title: string;
  intro?: string;
  endpoints: EndpointSpec[];
}

function renderValue(value: unknown, depth = 0): React.ReactNode {
  if (value === null || value === undefined) return <span className="text-gray-400">—</span>;
  if (typeof value === 'boolean') return <Badge variant={value ? 'default' : 'secondary'}>{String(value)}</Badge>;
  if (typeof value === 'number' || typeof value === 'string') return <span>{String(value)}</span>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-400">[] 空</span>;
    if (value.every((v) => v === null || typeof v !== 'object')) {
      return <span>{value.map((v) => String(v)).join(', ')}</span>;
    }
    return (
      <div className="space-y-2">
        {value.map((v, i) => (
          <div key={i} className="border rounded p-2 bg-gray-50">
            {renderValue(v, depth + 1)}
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === 'object') {
    return (
      <div className={depth === 0 ? 'space-y-1' : 'space-y-1'}>
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="flex gap-2 text-sm">
            <span className="text-gray-500 shrink-0 min-w-[180px]">{k}</span>
            <div className="flex-1">{renderValue(v, depth + 1)}</div>
          </div>
        ))}
      </div>
    );
  }
  return <span>{String(value)}</span>;
}

export function EndpointPanel({ title, intro, endpoints }: EndpointPanelProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, unknown>>({});
  // Serialise the endpoint spec so the fetch effect is not retriggered by a new
  // array/object identity on every render.
  const specKey = JSON.stringify(endpoints);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const specs: EndpointSpec[] = JSON.parse(specKey);
      const entries = await Promise.all(
        specs.map(async (ep) => {
          try {
            const res =
              ep.method === 'post'
                ? await api.post(ep.path, ep.body ?? {}, { params: ep.params })
                : await api.get(ep.path, { params: ep.params });
            return [ep.label, res.data] as const;
          } catch (err: any) {
            return [ep.label, { error: err.response?.data?.detail || err.message }] as const;
          }
        }),
      );
      setResults(Object.fromEntries(entries));
    } catch (err: any) {
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [specKey]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>
      {intro && <div className="text-sm text-gray-600">{intro}</div>}
      {error && <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">{error}</div>}

      {loading ? (
        <div className="flex items-center justify-center h-48"><div className="text-gray-500">加载中...</div></div>
      ) : (
        endpoints.map((ep) => (
          <Card key={ep.label}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span>{ep.label}</span>
                <Badge variant="secondary">{(ep.method || 'get').toUpperCase()} {ep.path}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {renderValue(results[ep.label])}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
