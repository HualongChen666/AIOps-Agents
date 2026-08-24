'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Link2, RefreshCw, Network } from 'lucide-react';

interface AlertCorrelation {
  id: string;
  alert_id: string;
  alert_title: string;
  related_alerts: Array<{
    alert_id: string;
    alert_title: string;
    correlation_score: number;
    correlation_type: 'temporal' | 'causal' | 'semantic';
  }>;
  correlation_group: string;
  created_at: string;
}

interface CorrelationStats {
  total_correlations: number;
  correlation_groups: number;
  avg_correlation_score: number;
  high_confidence_correlations: number;
}

export default function AlertCorrelationPage() {
  const [selectedCorrelation, setSelectedCorrelation] = useState<AlertCorrelation | null>(null);
  const [filters, setFilters] = useState({
    minScore: '0',
    search: '',
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showError = toast.error;

  const { data: correlationsData, isLoading: correlationsLoading, error: correlationsError, refetch: refetchCorrelations } = useQuery<AlertCorrelation[]>({
    queryKey: ['alert-correlations'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/correlation');
      return resp.data.correlations || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery<CorrelationStats>({
    queryKey: ['correlation-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/correlation/stats');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (correlationsError) showError('Failed to load alert correlations');
  }, [correlationsError, showError]);

  const filteredCorrelations = (correlationsData || []).filter((correlation) => {
    const minScore = parseFloat(filters.minScore);
    if (minScore > 0 && !correlation.related_alerts.some(r => r.correlation_score >= minScore)) return false;
    if (debouncedSearch && !correlation.alert_title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const getCorrelationTypeColor = (type: string) => {
    switch (type) {
      case 'temporal':
        return 'bg-blue-100 text-blue-800';
      case 'causal':
        return 'bg-red-100 text-red-800';
      case 'semantic':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCorrelationTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      temporal: '时间',
      causal: '因果',
      semantic: '语义',
    };
    return labels[type] || type;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  if (correlationsLoading || statsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link2 className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警关联</h1>
            <p className="text-sm text-gray-500">查看告警之间的关联关系</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => { refetchCorrelations(); refetchStats(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {statsData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              关联统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">总关联数</div>
                <div className="text-2xl font-bold text-[var(--accent-blue)]">{statsData.total_correlations}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">关联组数</div>
                <div className="text-2xl font-bold text-[var(--accent-green)]">{statsData.correlation_groups}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">平均关联度</div>
                <div className="text-2xl font-bold text-[var(--accent-yellow)]">{(statsData.avg_correlation_score * 100).toFixed(1)}%</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">高置信度关联</div>
                <div className="text-2xl font-bold text-[var(--accent-cyan)]">{statsData.high_confidence_correlations}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">最小关联度</label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={filters.minScore}
                onChange={(e) => setFilters({ ...filters, minScore: e.target.value })}
                placeholder="0.5"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <Input
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="搜索告警标题"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>告警关联 ({filteredCorrelations.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>告警标题</TableHead>
                <TableHead>关联组</TableHead>
                <TableHead>相关告警数</TableHead>
                <TableHead>最高关联度</TableHead>
                <TableHead>关联类型</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCorrelations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState
                      title="没有关联数据"
                      description="当前没有告警关联数据"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredCorrelations.map((correlation) => {
                  const maxScore = Math.max(...correlation.related_alerts.map(r => r.correlation_score));
                  return (
                    <TableRow key={correlation.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{correlation.alert_title}</TableCell>
                      <TableCell className="font-mono text-sm">{correlation.correlation_group}</TableCell>
                      <TableCell className="text-sm">{correlation.related_alerts.length}</TableCell>
                      <TableCell>
                        <Badge className={getScoreColor(maxScore)}>
                          {(maxScore * 100).toFixed(1)}%
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {Array.from(new Set(correlation.related_alerts.map(r => r.correlation_type))).map((type, idx) => (
                            <Badge key={idx} className={getCorrelationTypeColor(type)}>
                              {getCorrelationTypeLabel(type)}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(correlation.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedCorrelation(correlation)}
                        >
                          查看详情
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!selectedCorrelation} onOpenChange={() => setSelectedCorrelation(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>关联详情</DialogTitle>
          </DialogHeader>
          {selectedCorrelation && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警标题</label>
                <div className="text-lg font-semibold">{selectedCorrelation.alert_title}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">关联组</label>
                <div className="text-sm font-mono">{selectedCorrelation.correlation_group}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">相关告警</label>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>告警标题</TableHead>
                      <TableHead>关联度</TableHead>
                      <TableHead>关联类型</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selectedCorrelation.related_alerts.map((related, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{related.alert_title}</TableCell>
                        <TableCell>
                          <Badge className={getScoreColor(related.correlation_score)}>
                            {(related.correlation_score * 100).toFixed(1)}%
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getCorrelationTypeColor(related.correlation_type)}>
                            {getCorrelationTypeLabel(related.correlation_type)}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">创建时间</label>
                <div className="text-sm text-gray-600">{new Date(selectedCorrelation.created_at).toLocaleString()}</div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedCorrelation(null)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
