'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RealtimeEvent {
  id: number;
  stream_id: string | null;
  event_type: string;
  event_data: Record<string, unknown>;
  timestamp: string;
}

export function EventsPanel({ title, intro }: { title: string; intro?: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/realtime/events');
      setEvents(Array.isArray(res.data) ? res.data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载实时事件失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>
      {intro && <div className="text-sm text-gray-600">{intro}</div>}

      <Card>
        <CardHeader><CardTitle>实时事件（{events.length}）</CardTitle></CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无实时事件</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-600">
                  <th className="py-2">ID</th><th className="py-2">事件类型</th><th className="py-2">流</th><th className="py-2">时间</th><th className="py-2">数据</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id} className="border-b">
                    <td className="py-2 font-mono">{e.id}</td>
                    <td className="py-2"><Badge variant="secondary">{e.event_type}</Badge></td>
                    <td className="py-2">{e.stream_id || '—'}</td>
                    <td className="py-2">{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</td>
                    <td className="py-2 font-mono text-xs text-gray-500">{JSON.stringify(e.event_data)?.slice(0, 60)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
