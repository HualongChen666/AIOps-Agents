'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface SLOIncident {
  id: string;
  slo_id: string;
  slo_name: string;
  severity: 'critical' | 'major' | 'minor';
  start_time: string;
  end_time?: string;
  duration: number;
  impact: string;
  status: 'open' | 'resolved';
  description: string;
}

export default function SLOIncidentPage() {
  const [incidents, setIncidents] = useState<SLOIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIncidents();
  }, []);

  const fetchIncidents = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/incident');
      setIncidents(res.data.incidents || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载事件失败');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'major': return 'bg-orange-100 text-orange-800';
      case 'minor': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchIncidents} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO事件</h1>
        <Button onClick={fetchIncidents}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>事件列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SLO</TableHead>
                <TableHead>严重程度</TableHead>
                <TableHead>开始时间</TableHead>
                <TableHead>持续时间</TableHead>
                <TableHead>影响</TableHead>
                <TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {incidents.map((incident) => (
                <TableRow key={incident.id}>
                  <TableCell className="font-medium">{incident.slo_name}</TableCell>
                  <TableCell>
                    <Badge className={getSeverityColor(incident.severity)}>
                      {incident.severity}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(incident.start_time).toLocaleString()}
                  </TableCell>
                  <TableCell>{incident.duration}min</TableCell>
                  <TableCell className="text-sm">{incident.impact}</TableCell>
                  <TableCell>
                    <Badge variant={incident.status === 'open' ? 'destructive' : 'default'}>
                      {incident.status === 'open' ? '进行中' : '已解决'}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
