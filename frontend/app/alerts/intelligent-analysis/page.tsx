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
import { Brain, AlertTriangle, CheckCircle, XCircle, RefreshCw, Sparkles, TrendingUp } from 'lucide-react';

interface IntelligentAnalysis {
  id: string;
  alert_id: string;
  alert_title: string;
  analysis_type: 'root_cause' | 'pattern' | 'prediction' | 'correlation';
  confidence: number;
  insights: string[];
  recommendations: string[];
  related_alerts: string[];
  severity: 'critical' | 'high' | 'medium' | 'low';
  created_at: string;
  status: 'pending' | 'completed' | 'failed';
}

interface AnalysisStats {
  total_analyses: number;
  successful_analyses: number;
  failed_analyses: number;
  avg_confidence: number;
  pattern_count: number;
  root_cause_count: number;
}

export default function IntelligentAnalysisPage() {
  const [selectedAnalysis, setSelectedAnalysis] = useState<IntelligentAnalysis | null>(null);
  const [filters, setFilters] = useState({
    analysis_type: 'all',
    status: 'all',
    search: '',
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const { data: analysesData, isLoading: analysesLoading, error: analysesError, refetch: refetchAnalyses } = useQuery<IntelligentAnalysis[]>({
    queryKey: ['intelligent-analyses'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/intelligent-analysis');
      return resp.data.analyses || resp.data || [];
    },
    refetchInterval: 20000,
  });

  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery<AnalysisStats>({
    queryKey: ['intelligent-analysis-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/intelligent-analysis/stats');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const handleRunAnalysis = async () => {
    try {
      await api.post('/api/v1/alerts/intelligent-analysis/run');
      showSuccess('智能分析已启动');
      await refetchAnalyses();
    } catch (error) {
      showError('启动分析失败');
    }
  };

  useEffect(() => {
    if (analysesError) showError('Failed to load intelligent analyses');
  }, [analysesError, showError]);

  const filteredAnalyses = (analysesData || []).filter((analysis) => {
    if (filters.analysis_type !== 'all' && analysis.analysis_type !== filters.analysis_type) return false;
    if (filters.status !== 'all' && analysis.status !== filters.status) return false;
    if (debouncedSearch && !analysis.alert_title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const getAnalysisTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      root_cause: 'bg-red-100 text-red-800',
      pattern: 'bg-blue-100 text-blue-800',
      prediction: 'bg-purple-100 text-purple-800',
      correlation: 'bg-green-100 text-green-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getAnalysisTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      root_cause: '根因分析',
      pattern: '模式识别',
      prediction: '预测分析',
      correlation: '关联分析',
    };
    return labels[type] || type;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  if (analysesLoading || statsLoading) {
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
          <Brain className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">智能告警分析</h1>
            <p className="text-sm text-gray-500">AI驱动的告警智能分析和洞察</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleRunAnalysis}>
            <Sparkles className="h-4 w-4 mr-2" />
            运行分析
          </Button>
          <Button onClick={() => { refetchAnalyses(); refetchStats(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      {statsData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              分析统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">总分析数</div>
                <div className="text-2xl font-bold text-[var(--accent-blue)]">{statsData.total_analyses}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">成功分析</div>
                <div className="text-2xl font-bold text-[var(--accent-green)]">{statsData.successful_analyses}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">失败分析</div>
                <div className="text-2xl font-bold text-[var(--accent-red)]">{statsData.failed_analyses}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">平均置信度</div>
                <div className="text-2xl font-bold text-[var(--accent-yellow)]">{(statsData.avg_confidence * 100).toFixed(1)}%</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">模式数</div>
                <div className="text-2xl font-bold text-[var(--accent-cyan)]">{statsData.pattern_count}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分析类型</label>
              <Select
                value={filters.analysis_type}
                onChange={(e) => setFilters({ ...filters, analysis_type: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="root_cause">根因分析</option>
                <option value="pattern">模式识别</option>
                <option value="prediction">预测分析</option>
                <option value="correlation">关联分析</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <Select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="completed">已完成</option>
                <option value="pending">进行中</option>
                <option value="failed">失败</option>
              </Select>
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

      {/* 分析列表 */}
      <Card>
        <CardHeader>
          <CardTitle>分析结果 ({filteredAnalyses.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>告警标题</TableHead>
                <TableHead>分析类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>置信度</TableHead>
                <TableHead>严重度</TableHead>
                <TableHead>洞察数</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAnalyses.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState
                      title="没有分析结果"
                      description="当前没有智能分析结果"
                      action={<Button onClick={handleRunAnalysis}>运行第一次分析</Button>}
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAnalyses.map((analysis) => (
                  <TableRow key={analysis.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{analysis.alert_title}</TableCell>
                    <TableCell>
                      <Badge className={getAnalysisTypeColor(analysis.analysis_type)}>
                        {getAnalysisTypeLabel(analysis.analysis_type)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(analysis.status)}>
                        {analysis.status === 'completed' ? '已完成' : analysis.status === 'pending' ? '进行中' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getConfidenceColor(analysis.confidence)}>
                        {(analysis.confidence * 100).toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={analysis.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}>
                        {analysis.severity}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{analysis.insights.length}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(analysis.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedAnalysis(analysis)}
                      >
                        查看详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 分析详情对话框 */}
      <Dialog open={!!selectedAnalysis} onOpenChange={() => setSelectedAnalysis(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              智能分析详情
            </DialogTitle>
          </DialogHeader>
          {selectedAnalysis && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警标题</label>
                <div className="text-lg font-semibold">{selectedAnalysis.alert_title}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">分析类型</label>
                  <Badge className={getAnalysisTypeColor(selectedAnalysis.analysis_type)}>
                    {getAnalysisTypeLabel(selectedAnalysis.analysis_type)}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">置信度</label>
                  <Badge className={getConfidenceColor(selectedAnalysis.confidence)}>
                    {(selectedAnalysis.confidence * 100).toFixed(1)}%
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">AI洞察</label>
                <div className="space-y-2">
                  {selectedAnalysis.insights.map((insight, idx) => (
                    <div key={idx} className="text-sm bg-blue-50 p-3 rounded border-l-4 border-blue-500">
                      {insight}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">建议措施</label>
                <div className="space-y-2">
                  {selectedAnalysis.recommendations.map((rec, idx) => (
                    <div key={idx} className="text-sm bg-green-50 p-3 rounded border-l-4 border-green-500">
                      {rec}
                    </div>
                  ))}
                </div>
              </div>
              {selectedAnalysis.related_alerts && selectedAnalysis.related_alerts.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">相关告警</label>
                  <div className="flex flex-wrap gap-2">
                    {selectedAnalysis.related_alerts.map((alertId, idx) => (
                      <Badge key={idx} variant="outline" className="font-mono">
                        {alertId}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">创建时间</label>
                <div className="text-sm text-gray-600">{new Date(selectedAnalysis.created_at).toLocaleString()}</div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedAnalysis(null)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
