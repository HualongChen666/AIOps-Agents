'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RealtimeStatus {
  connections: number;
  rooms: Record<string, number>;
  timestamp: string;
}

export default function RealtimeStatusPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<RealtimeStatus | null>(null);
  const [wsCount, setWsCount] = useState(0);
  const [sseCount, setSseCount] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusRes, streamRes] = await Promise.all([
        api.get('/api/realtime/status'),
        api.get('/api/v1/realtime/streams'),
      ]);
      setStatus(statusRes.data);
      const streams = Array.isArray(streamRes.data) ? streamRes.data : [];
      setWsCount(streams.filter((s: any) => s.stream_type === 'websocket').length);
      setSseCount(streams.filter((s: any) => s.stream_type === 'sse').length);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载实时状态失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 10000);
    return () => clearInterval(timer);
  }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  const rooms = status?.rooms ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">实时通信状态</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">活跃连接</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{status?.connections ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">WebSocket 流</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{wsCount}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">SSE 流</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{sseCount}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>房间连接数</CardTitle></CardHeader>
        <CardContent>
          {Object.keys(rooms).length === 0 ? (
            <div className="text-gray-500 text-center py-6">当前无活跃房间连接</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(rooms).map(([room, n]) => (
                <div key={room} className="border rounded p-3 flex items-center justify-between">
                  <span>{room}</span>
                  <Badge variant="secondary">{n}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>统计时间</CardTitle></CardHeader>
        <CardContent><div className="text-sm text-gray-600">{status?.timestamp ? new Date(status.timestamp).toLocaleString() : '—'}</div></CardContent>
      </Card>
    </div>
  );
}
