'use client'

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface RootCauseNode {
  id: string;
  name: string;
  type: 'service' | 'component' | 'metric';
  status: 'normal' | 'warning' | 'critical';
  impact: number;
}

interface AnalysisReport {
  id: string;
  timestamp: string;
  alertId: string;
  rootCause: string;
  confidence: number;
  affectedServices: string[];
  recommendations: string[];
}

export default function RCAPage() {
  const [selectedAlert, setSelectedAlert] = useState('ALT-001');
  const [analysisReports, setAnalysisReports] = useState<AnalysisReport[]>([]);
  const [rootCauseNodes, setRootCauseNodes] = useState<RootCauseNode[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [hypothesesRes, patternsRes] = await Promise.all([
          api.get('/api/v1/root-cause/hypotheses'),
          api.get('/api/v1/root-cause/patterns'),
        ]);

        const hypotheses = hypothesesRes.data?.hypotheses || [];
        setRootCauseNodes(
          hypotheses.map((h: any) => ({
            id: h.hypothesis_id,
            name: h.root_cause,
            type: 'service' as const,
            status:
              h.confidence >= 0.8 ? 'critical' : h.confidence >= 0.5 ? 'warning' : 'normal',
            impact: h.impact_score ?? h.confidence ?? 0,
          }))
        );

        const patterns = patternsRes.data?.patterns || [];
        setAnalysisReports(
          patterns.map((p: any) => ({
            id: p.pattern_id,
            timestamp: p.last_occurrence || new Date().toISOString(),
            alertId: p.pattern_id,
            rootCause: p.root_cause,
            confidence: Math.round((p.confidence ?? 0) * 100),
            affectedServices: [],
            recommendations: [],
          }))
        );
      } catch (error) {
        console.error('Failed to fetch root cause data:', error);
      }
    };

    fetchData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'normal':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'service':
        return '🔧';
      case 'component':
        return '⚙️';
      case 'metric':
        return '📊';
      default:
        return '📦';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">根因分析</h1>
        <Button>开始分析</Button>
      </div>

      {/* 根因图谱 */}
      <Card>
        <CardHeader>
          <CardTitle>根因图谱</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center relative">
            <p className="text-gray-500">根因图谱区域 (使用@antv/g6渲染)</p>
            <div className="absolute top-4 right-4 space-x-2">
              <Badge className="bg-red-100 text-red-800">严重</Badge>
              <Badge className="bg-yellow-100 text-yellow-800">警告</Badge>
              <Badge className="bg-green-100 text-green-800">正常</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 影响分析 */}
      <Card>
        <CardHeader>
          <CardTitle>影响分析</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>节点</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>影响度</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rootCauseNodes.map((node) => (
                <TableRow key={node.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <span>{getTypeIcon(node.type)}</span>
                      <span>{node.name}</span>
                    </div>
                  </TableCell>
                  <TableCell>{node.type}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(node.status)}>
                      {node.status === 'critical' ? '严重' : node.status === 'warning' ? '警告' : '正常'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600"
                          style={{ width: `${node.impact * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">{(node.impact * 100).toFixed(0)}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 分析报告 */}
      <Card>
        <CardHeader>
          <CardTitle>分析报告</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>时间</TableHead>
                <TableHead>告警ID</TableHead>
                <TableHead>根因</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>影响服务</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {analysisReports.map((report) => (
                <TableRow key={report.id}>
                  <TableCell className="font-mono text-sm">{report.id}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(report.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{report.alertId}</TableCell>
                  <TableCell className="font-medium">{report.rootCause}</TableCell>
                  <TableCell>
                    <Badge className={report.confidence > 90 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}>
                      {report.confidence}%
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {report.affectedServices.map((service) => (
                        <Badge key={service} variant="outline" className="text-xs">
                          {service}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 修复建议 */}
      <Card>
        <CardHeader>
          <CardTitle>修复建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {analysisReports[0]?.recommendations.map((rec, idx) => (
              <div key={idx} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{rec}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      预计可解决 {analysisReports[0]?.confidence}% 的问题
                    </p>
                  </div>
                  <Button variant="outline" size="sm">
                    应用
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
