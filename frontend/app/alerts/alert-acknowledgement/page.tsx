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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { CheckCircle, RefreshCw, MessageSquare, User } from 'lucide-react';

interface Acknowledgement {
  id: string;
  alert_id: string;
  alert_title: string;
  acknowledged_by: string;
  acknowledged_at: string;
  comment: string;
  status: 'acknowledged' | 'resolved';
  expires_at?: string;
}

export default function AlertAcknowledgementPage() {
  const [selectedAck, setSelectedAck] = useState<Acknowledgement | null>(null);
  const [filters, setFilters] = useState({
    status: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [selectedAlertId, setSelectedAlertId] = useState('');
  const [comment, setComment] = useState('');

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: acksData, isLoading: acksLoading, error: acksError, refetch: refetchAcks } = useQuery<Acknowledgement[]>({
    queryKey: ['alert-acknowledgements'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/acknowledgements');
      return resp.data.acknowledgements || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: async ({ alertId, comment }: { alertId: string; comment: string }) => {
      const resp = await api.post(`/api/v1/alerts/${alertId}/acknowledge`, { comment });
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('告警已确认');
      setShowDialog(false);
      setComment('');
      setSelectedAlertId('');
      queryClient.invalidateQueries({ queryKey: ['alert-acknowledgements'] });
    },
    onError: () => showError('确认告警失败'),
  });

  useEffect(() => {
    if (acksError) showError('Failed to load acknowledgements');
  }, [acksError, showError]);

  const filteredAcks = (acksData || []).filter((ack) => {
    if (filters.status !== 'all' && ack.status !== filters.status) return false;
    if (debouncedSearch && !ack.alert_title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleAcknowledge = () => {
    if (!selectedAlertId) return;
    acknowledgeMutation.mutate({ alertId: selectedAlertId, comment });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'acknowledged':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (acksLoading) {
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
          <CheckCircle className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警确认</h1>
            <p className="text-sm text-gray-500">查看和管理告警确认记录</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowDialog(true)}>
            <MessageSquare className="h-4 w-4 mr-2" />
            确认告警
          </Button>
          <Button onClick={() => refetchAcks()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
              <Select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="all">全部</option>
                <option value="acknowledged">已确认</option>
                <option value="resolved">已解决</option>
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

      <Card>
        <CardHeader>
          <CardTitle>确认记录 ({filteredAcks.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>告警标题</TableHead>
                <TableHead>确认人</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>评论</TableHead>
                <TableHead>确认时间</TableHead>
                <TableHead>过期时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAcks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <EmptyState
                      title="没有确认记录"
                      description="当前没有告警确认记录"
                    />
                  </TableCell>
                </TableRow>
              ) : (
                filteredAcks.map((ack) => (
                  <TableRow key={ack.id} className="cursor-pointer hover:bg-gray-50">
                    <TableCell className="font-medium">{ack.alert_title}</TableCell>
                    <TableCell className="text-sm">{ack.acknowledged_by}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(ack.status)}>
                        {ack.status === 'acknowledged' ? '已确认' : '已解决'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500 truncate max-w-xs">{ack.comment || '-'}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(ack.acknowledged_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {ack.expires_at ? new Date(ack.expires_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedAck(ack)}
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

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认告警</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">告警ID</label>
              <Input
                value={selectedAlertId}
                onChange={(e) => setSelectedAlertId(e.target.value)}
                placeholder="输入告警ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">评论</label>
              <Input
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="输入确认评论"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>取消</Button>
            <Button onClick={handleAcknowledge} disabled={acknowledgeMutation.isPending}>
              确认
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!selectedAck} onOpenChange={() => setSelectedAck(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认详情</DialogTitle>
          </DialogHeader>
          {selectedAck && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警标题</label>
                <div className="text-lg font-semibold">{selectedAck.alert_title}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">确认人</label>
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span className="text-sm">{selectedAck.acknowledged_by}</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={getStatusColor(selectedAck.status)}>
                    {selectedAck.status}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">评论</label>
                <div className="text-sm bg-gray-100 p-2 rounded">{selectedAck.comment || '-'}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">确认时间</label>
                  <div className="text-sm text-gray-600">{new Date(selectedAck.acknowledged_at).toLocaleString()}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">过期时间</label>
                  <div className="text-sm text-gray-600">{selectedAck.expires_at ? new Date(selectedAck.expires_at).toLocaleString() : '-'}</div>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedAck(null)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
