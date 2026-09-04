'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { FileText, Search, RefreshCw, Shield, AlertTriangle, CheckCircle, XCircle, Download } from 'lucide-react';
import * as XLSX from 'xlsx';

interface AuditLog {
  trace_id?: string;
  timestamp: string;
  who: string;
  where: string;
  what: string;
  risk_level: 'safe' | 'low' | 'medium' | 'high' | 'blocked';
  result: string;
  executor?: string;
  source_ip?: string;
}

export default function AuditPage() {
  const [riskLevelFilter, setRiskLevelFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 🔧 获取审计日志
  const { data: auditData, isLoading, error, refetch } = useQuery<{
    total: number;
    filter: { risk_level?: string };
    logs: AuditLog[];
  }>({
    queryKey: ['audit-logs', riskLevelFilter],
    queryFn: async () => {
      const riskParam = riskLevelFilter === 'all' ? undefined : riskLevelFilter;
      const resp = await api.get(`/api/guard/audit?limit=100${riskParam ? `&risk_level=${riskParam}` : ''}`);
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(isLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 规范化审计日志数据
  const [logs, setLogs] = useState<AuditLog[]>([]);

  useEffect(() => {
    if (auditData?.logs) {
      setLogs(auditData.logs);
    }
  }, [auditData]);

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (error) {
      showError('Failed to load audit logs');
      setPageError(error as Error);
    }
  }, [error, showError, setPageError]);

  const filteredLogs = logs.filter((log) => {
    if (searchQuery && !log.what.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'safe':
        return 'bg-green-100 text-green-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'blocked':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getResultIcon = (result: string) => {
    if (result === 'allowed' || result === 'approved') {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
    if (result === 'blocked' || result === 'rejected') {
      return <XCircle className="h-4 w-4 text-red-500" />;
    }
    return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
  };

  // 🔧 Export to CSV/Excel
  const exportToCSV = () => {
    const csvData = filteredLogs.map(log => ({
      '时间': log.timestamp ? new Date(log.timestamp).toLocaleString() : '-',
      '执行者': log.who || log.executor || '-',
      '主机': log.where || '-',
      '命令': log.what || '-',
      '风险等级': log.risk_level || '-',
      '结果': log.result || '-',
      '来源IP': log.source_ip || '-',
    }));

    const ws = XLSX.utils.json_to_sheet(csvData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, '审计日志');
    XLSX.writeFile(wb, `audit_logs_${new Date().toISOString().split('T')[0]}.xlsx`);
    showSuccess('导出成功');
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载审计日志，请稍后重试"
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">审计日志</h1>
            <p className="text-sm text-gray-500">查看系统操作审计记录</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={exportToCSV} variant="outline">
            <Download className="h-4 w-4 mr-2" />
            导出Excel
          </Button>
        </div>
      </div>

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
              <Select
                value={riskLevelFilter}
                onChange={(e) => setRiskLevelFilter(e.target.value)}
              >
                <option value="all">全部</option>
                <option value="safe">安全</option>
                <option value="low">低风险</option>
                <option value="medium">中风险</option>
                <option value="high">高风险</option>
                <option value="blocked">已拦截</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索命令内容"
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 审计日志列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            审计记录 ({filteredLogs.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredLogs.length === 0 ? (
            <EmptyState
              title="暂无审计日志"
              description="当前没有符合条件的审计记录"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>执行者</TableHead>
                  <TableHead>主机</TableHead>
                  <TableHead>命令</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>结果</TableHead>
                  <TableHead>来源IP</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log, index) => (
                  <TableRow key={log.trace_id || index} className="hover:bg-gray-50">
                    <TableCell className="text-sm text-gray-500">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="font-medium">{log.who || log.executor || '-'}</TableCell>
                    <TableCell>{log.where || '-'}</TableCell>
                    <TableCell className="font-mono text-sm max-w-md truncate">
                      {log.what || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge className={getRiskLevelColor(log.risk_level)}>
                        {log.risk_level}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getResultIcon(log.result)}
                        <span className="text-sm">{log.result || '-'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {log.source_ip || '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}