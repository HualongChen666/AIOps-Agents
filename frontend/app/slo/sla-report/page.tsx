'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface SLAReport {
  id: string;
  slo_id: string;
  slo_name: string;
  service: string;
  metric: string;
  period: string;
  availability: number;
  slaTarget: number;
  compliance: string;
  incidents: number;
  aggregation: string | null;
}

export default function SLAReportPage() {
  const [reports, setReports] = useState<SLAReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState('30d');

  const generateReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post('/api/v1/slo/reports', null, { params: { period } });
      setReports(res.data.reports || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '生成报告失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    generateReport();
  }, []);

  const isCompliant = (report: SLAReport) => report.compliance === 'compliant';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLA报告</h1>
        <div className="flex gap-2">
          <Input
            placeholder="报告周期"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="w-40"
          />
          <Button onClick={generateReport} disabled={loading}>
            {loading ? '生成中...' : '生成报告'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reports.map((report) => (
          <Card key={report.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{report.slo_name}</CardTitle>
                <Badge variant={isCompliant(report) ? 'default' : 'destructive'}>
                  {isCompliant(report) ? '合规' : '违规'}
                </Badge>
              </div>
              <div className="text-sm text-gray-500">
                {report.service} · {report.metric}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">可用性</span>
                    <span className="font-semibold">{report.availability.toFixed(2)}% / {report.slaTarget}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${isCompliant(report) ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(report.availability, 100)}%` }}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">事件数</div>
                    <div className="text-lg font-semibold">{report.incidents}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">聚合方式</div>
                    <div className="text-sm font-mono">{report.aggregation || 'good_ratio'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">周期</div>
                    <div className="text-sm">{report.period}</div>
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
