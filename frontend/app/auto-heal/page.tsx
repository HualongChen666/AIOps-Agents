'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface HealTask {
  id: string;
  alertId: string;
  alertTitle: string;
  healPlan: string;
  riskLevel: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed' | 'failed';
  createdAt: string;
  approver?: string;
  approvalComment?: string;
}

export default function AutoHealPage() {
  const [tasks, setTasks] = useState<HealTask[]>([]);

  const [selectedTab, setSelectedTab] = useState<'pending' | 'approved' | 'executing' | 'completed' | 'failed'>('pending');
  const [selectedTask, setSelectedTask] = useState<HealTask | null>(null);
  const [approvalComment, setApprovalComment] = useState('');

  const loadTasks = async () => {
    try {
      const resp = await api.get('/api/v1/approvals/pending');
      const items = resp.data?.items || [];
      setTasks(
        items.map((item: any) => ({
          id: item.alert_id || item.id || String(Date.now()),
          alertId: item.alert_id || item.id || '',
          alertTitle: item.title || item.alert_id || '修复方案',
          healPlan: item.proposal || item.heal_plan || item.description || '',
          riskLevel: (item.risk_level || 'low') as 'low' | 'medium' | 'high',
          status: (item.status || 'pending') as HealTask['status'],
          createdAt: item.created_at || item.timestamp || new Date().toISOString(),
          approver: item.approver || '',
          approvalComment: item.approval_comment || '',
        }))
      );
    } catch (err) {
      console.error('加载待审批修复方案失败:', err);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const filteredTasks = tasks.filter((task) => task.status === selectedTab);

  const handleApprove = async () => {
    if (!selectedTask) return;
    try {
      await api.patch(`/api/v1/approvals/${selectedTask.alertId}`);
      await loadTasks();
    } catch (err) {
      console.error('批准失败:', err);
    } finally {
      setSelectedTask(null);
      setApprovalComment('');
    }
  };

  const handleReject = async () => {
    if (!selectedTask) return;
    try {
      await api.post('/api/v1/approvals/reject', {
        alert_id: selectedTask.alertId,
        reason: approvalComment || '人工驳回',
      });
      await loadTasks();
    } catch (err) {
      console.error('驳回失败:', err);
    } finally {
      setSelectedTask(null);
      setApprovalComment('');
    }
  };

  const handleExecute = async (taskId: string) => {
    try {
      await api.patch(`/api/v1/approvals/${taskId}`);
      await loadTasks();
    } catch (err) {
      console.error('执行失败:', err);
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      case 'approved':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'executing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'pending' as const, label: '待审批', count: tasks.filter(t => t.status === 'pending').length },
    { key: 'approved' as const, label: '已批准', count: tasks.filter(t => t.status === 'approved').length },
    { key: 'executing' as const, label: '执行中', count: tasks.filter(t => t.status === 'executing').length },
    { key: 'completed' as const, label: '已完成', count: tasks.filter(t => t.status === 'completed').length },
    { key: 'failed' as const, label: '失败', count: tasks.filter(t => t.status === 'failed').length },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">自动修复</h1>
        <Button onClick={loadTasks}>刷新</Button>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSelectedTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${selectedTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 修复任务列表 */}
      <Card>
        <CardHeader>
          <CardTitle>
            {selectedTab === 'pending' ? '待审批' : selectedTab === 'approved' ? '已批准' : selectedTab === 'executing' ? '执行中' : selectedTab === 'completed' ? '已完成' : '失败'}任务
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>告警</TableHead>
                <TableHead>修复方案</TableHead>
                <TableHead>风险等级</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>审批人</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="font-mono text-sm">{task.id}</TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{task.alertTitle}</p>
                      <p className="text-sm text-gray-500">{task.alertId}</p>
                    </div>
                  </TableCell>
                  <TableCell>{task.healPlan}</TableCell>
                  <TableCell>
                    <Badge className={getRiskColor(task.riskLevel)}>
                      {task.riskLevel === 'low' ? '低' : task.riskLevel === 'medium' ? '中' : '高'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(task.status)}>
                      {task.status === 'pending' ? '待审批' :
                        task.status === 'approved' ? '已批准' :
                          task.status === 'rejected' ? '已拒绝' :
                            task.status === 'completed' ? '已完成' : '失败'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(task.createdAt).toLocaleString()}
                  </TableCell>
                  <TableCell>{task.approver || '-'}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {task.status === 'pending' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedTask(task)}
                        >
                          审批
                        </Button>
                      )}
                      {task.status === 'approved' && (
                        <Button
                          size="sm"
                          onClick={() => handleExecute(task.id)}
                          disabled={false}
                        >
                          执行
                        </Button>
                      )}
                      {task.status === 'completed' && (
                        <Button variant="ghost" size="sm">
                          查看日志
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 审批弹窗 */}
      {selectedTask && (
        <Dialog open={!!selectedTask} onOpenChange={() => setSelectedTask(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>审批修复任务 - {selectedTask.id}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">告警信息</label>
                <p className="mt-1 text-sm text-gray-900">{selectedTask.alertTitle}</p>
                <p className="text-sm text-gray-500">{selectedTask.alertId}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">修复方案</label>
                <p className="mt-1 text-sm text-gray-900">{selectedTask.healPlan}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">风险等级</label>
                <Badge className={getRiskColor(selectedTask.riskLevel)}>
                  {selectedTask.riskLevel === 'low' ? '低' : selectedTask.riskLevel === 'medium' ? '中' : '高'}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">审批意见</label>
                <Textarea
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  placeholder="请输入审批意见..."
                  rows={3}
                />
              </div>
              {selectedTask.riskLevel === 'high' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800 font-medium">⚠️ 高风险操作</p>
                  <p className="text-sm text-red-700">此操作可能对系统产生重大影响，请谨慎审批。</p>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setSelectedTask(null)}>
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
              >
                拒绝
              </Button>
              <Button onClick={handleApprove}>
                批准
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
