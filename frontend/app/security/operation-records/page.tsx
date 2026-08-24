'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface OperationRecord {
  id: string;
  timestamp: string;
  userId: string;
  operationType: string;
  target: string;
  status: 'success' | 'failed' | 'pending' | 'cancelled';
  duration: number;
  parameters: Record<string, any>;
  result: string;
  ipAddress: string;
  sessionId: string;
}

interface OperationStats {
  totalOperations: number;
  successRate: number;
  avgDuration: number;
  todayOperations: number;
}

export default function OperationRecordsPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [records, setRecords] = useState<OperationRecord[]>([]);
  const [stats, setStats] = useState<OperationStats>({
    totalOperations: 0,
    successRate: 0,
    avgDuration: 0,
    todayOperations: 0,
  });
  const [filters, setFilters] = useState({
    userId: '',
    operationType: '',
    status: '',
    target: '',
    startDate: '',
    endDate: '',
  });
  const [selectedRecord, setSelectedRecord] = useState<OperationRecord | null>(null);

  const loadOperationRecords = async () => {
    setLoading(true);
    try {
      const [recordsRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/operation-records', { params: filters }),
        api.get('/api/v1/security/operation-records/stats'),
      ]);

      const recordsData = recordsRes.data?.records || [];
      const statsData = statsRes.data || {};

      setRecords(recordsData);
      setStats({
        totalOperations: statsData.totalOperations || recordsData.length,
        successRate: statsData.successRate || 0,
        avgDuration: statsData.avgDuration || 0,
        todayOperations: statsData.todayOperations || 0,
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleViewDetails = (record: OperationRecord) => {
    setSelectedRecord(record);
  };

  const handleExportRecords = async () => {
    try {
      const response = await api.get('/api/v1/security/operation-records/export', {
        params: filters,
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `operation-records-${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      success('操作记录导出成功');
    } catch (err) {
      showError('导出失败');
    }
  };

  const handleSearch = () => {
    loadOperationRecords();
  };

  const handleResetFilters = () => {
    setFilters({
      userId: '',
      operationType: '',
      status: '',
      target: '',
      startDate: '',
      endDate: '',
    });
  };

  useEffect(() => {
    loadOperationRecords();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">操作记录</h1>
        <div className="flex gap-2">
          <Button onClick={loadOperationRecords}>刷新数据</Button>
          <Button onClick={handleExportRecords}>导出记录</Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总操作数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{stats.totalOperations}</p>
            <p className="text-sm text-gray-500">历史累计</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.successRate.toFixed(1)}%</p>
            <p className="text-sm text-gray-500">操作成功率</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均耗时</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{stats.avgDuration.toFixed(2)}s</p>
            <p className="text-sm text-gray-500">平均执行时间</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">今日操作</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{stats.todayOperations}</p>
            <p className="text-sm text-gray-500">今日执行</p>
          </CardContent>
        </Card>
      </div>

      {/* 筛选器 */}
      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <Input
              placeholder="用户ID"
              value={filters.userId}
              onChange={(e) => setFilters({ ...filters, userId: e.target.value })}
            />
            <Input
              placeholder="操作类型"
              value={filters.operationType}
              onChange={(e) => setFilters({ ...filters, operationType: e.target.value })}
            />
            <Input
              placeholder="目标"
              value={filters.target}
              onChange={(e) => setFilters({ ...filters, target: e.target.value })}
            />
            <Select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              <option value="">所有状态</option>
              <option value="success">成功</option>
              <option value="failed">失败</option>
              <option value="pending">进行中</option>
              <option value="cancelled">已取消</option>
            </Select>
            <Input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
            />
            <Input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
            />
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={handleSearch}>搜索</Button>
            <Button variant="outline" onClick={handleResetFilters}>重置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 操作记录列表 */}
      <Card>
        <CardHeader>
          <CardTitle>操作记录</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>用户</TableHead>
                <TableHead>操作类型</TableHead>
                <TableHead>目标</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>耗时</TableHead>
                <TableHead>IP地址</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.length > 0 ? records.map((record) => (
                <TableRow key={record.id}>
                  <TableCell>{new Date(record.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{record.userId}</TableCell>
                  <TableCell>{record.operationType}</TableCell>
                  <TableCell>{record.target}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(record.status)}>{record.status}</Badge>
                  </TableCell>
                  <TableCell>{record.duration}ms</TableCell>
                  <TableCell className="font-mono text-sm">{record.ipAddress}</TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewDetails(record)}
                    >
                      详情
                    </Button>
                  </TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-gray-500">
                    No operation records found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 详情模态框 */}
      {selectedRecord && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-3xl max-h-[80vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>操作详情</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">操作ID</label>
                  <p className="font-mono text-sm">{selectedRecord.id}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">时间</label>
                  <p>{new Date(selectedRecord.timestamp).toLocaleString()}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">用户</label>
                  <p>{selectedRecord.userId}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">操作类型</label>
                  <p>{selectedRecord.operationType}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">目标</label>
                  <p>{selectedRecord.target}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">状态</label>
                  <Badge className={getStatusColor(selectedRecord.status)}>{selectedRecord.status}</Badge>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">耗时</label>
                  <p>{selectedRecord.duration}ms</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">IP地址</label>
                  <p className="font-mono text-sm">{selectedRecord.ipAddress}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">会话ID</label>
                  <p className="font-mono text-sm">{selectedRecord.sessionId}</p>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">参数</label>
                <pre className="mt-1 p-3 bg-gray-100 dark:bg-gray-800 rounded text-sm overflow-auto">
                  {JSON.stringify(selectedRecord.parameters, null, 2)}
                </pre>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">结果</label>
                <p className="mt-1 p-3 bg-gray-100 dark:bg-gray-800 rounded text-sm">{selectedRecord.result}</p>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => setSelectedRecord(null)}>关闭</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
