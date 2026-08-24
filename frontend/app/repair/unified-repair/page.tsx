'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface UnifiedRepair {
  id: string;
  name: string;
  description: string;
  repairType: 'script' | 'configuration' | 'restart' | 'rollback' | 'custom';
  targetScope: string;
  status: 'draft' | 'pending' | 'approved' | 'executing' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  createdAt: string;
  createdBy: string;
  steps: Array<{
    order: number;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
  }>;
}

export default function UnifiedRepairPage() {
  const [repairs, setRepairs] = useState<UnifiedRepair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRepair, setSelectedRepair] = useState<UnifiedRepair | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    repairType: 'script' as UnifiedRepair['repairType'],
    targetScope: '',
    priority: 'medium' as UnifiedRepair['priority'],
  });

  const loadRepairs = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/unified');
      const items = resp.data?.items || [];
      setRepairs(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          name: item.name || '',
          description: item.description || '',
          repairType: (item.repair_type || 'script') as UnifiedRepair['repairType'],
          targetScope: item.target_scope || '',
          status: (item.status || 'draft') as UnifiedRepair['status'],
          priority: (item.priority || 'medium') as UnifiedRepair['priority'],
          createdAt: item.created_at || new Date().toISOString(),
          createdBy: item.created_by || 'System',
          steps: item.steps || [],
        }))
      );
    } catch (err: any) {
      console.error('加载统一修复失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepairs();
  }, []);

  const handleCreateRepair = async () => {
    try {
      await api.post('/api/v1/repair/unified', formData);
      setIsCreateDialogOpen(false);
      setFormData({ name: '', description: '', repairType: 'script', targetScope: '', priority: 'medium' });
      await loadRepairs();
    } catch (err: any) {
      console.error('创建修复失败:', err);
      setError(err.message || '创建失败');
    }
  };

  const handleExecuteRepair = async (repairId: string) => {
    try {
      await api.post(`/api/v1/repair/unified/${repairId}/execute`);
      await loadRepairs();
    } catch (err: any) {
      console.error('执行修复失败:', err);
      setError(err.message || '执行失败');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'pending':
        return 'bg-blue-100 text-blue-800';
      case 'approved':
        return 'bg-cyan-100 text-cyan-800';
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">统一修复</h1>
        <div className="flex gap-2">
          <Button onClick={loadRepairs} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            创建修复
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">草稿</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'draft').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">待执行</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'approved').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">执行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'executing').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{repairs.filter(r => r.status === 'completed').length}</div>
          </CardContent>
        </Card>
      </div>

      {/* 修复列表 */}
      <Card>
        <CardHeader>
          <CardTitle>统一修复任务</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : repairs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>修复类型</TableHead>
                  <TableHead>目标范围</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>创建者</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {repairs.map((repair) => (
                  <TableRow key={repair.id}>
                    <TableCell className="font-mono text-sm">{repair.id}</TableCell>
                    <TableCell className="font-medium">{repair.name}</TableCell>
                    <TableCell className="max-w-xs truncate">{repair.description}</TableCell>
                    <TableCell>{repair.repairType}</TableCell>
                    <TableCell className="font-mono text-sm">{repair.targetScope}</TableCell>
                    <TableCell>
                      <Badge className={getPriorityColor(repair.priority)}>
                        {repair.priority === 'low' ? '低' :
                         repair.priority === 'medium' ? '中' :
                         repair.priority === 'high' ? '高' : '严重'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(repair.status)}>
                        {repair.status === 'draft' ? '草稿' :
                         repair.status === 'pending' ? '待审批' :
                         repair.status === 'approved' ? '已批准' :
                         repair.status === 'executing' ? '执行中' :
                         repair.status === 'completed' ? '已完成' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(repair.createdAt).toLocaleString()}
                    </TableCell>
                    <TableCell>{repair.createdBy}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedRepair(repair)}
                        >
                          查看
                        </Button>
                        {repair.status === 'approved' && (
                          <Button
                            size="sm"
                            onClick={() => handleExecuteRepair(repair.id)}
                          >
                            执行
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 查看详情弹窗 */}
      {selectedRepair && (
        <Dialog open={!!selectedRepair} onOpenChange={() => setSelectedRepair(null)}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{selectedRepair.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">描述</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRepair.description}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">修复类型</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRepair.repairType}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">目标范围</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedRepair.targetScope}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">优先级</label>
                  <Badge className={getPriorityColor(selectedRepair.priority)}>
                    {selectedRepair.priority === 'low' ? '低' :
                     selectedRepair.priority === 'medium' ? '中' :
                     selectedRepair.priority === 'high' ? '高' : '严重'}
                  </Badge>
                </div>
              </div>
              {selectedRepair.steps.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">执行步骤</label>
                  <div className="space-y-2">
                    {selectedRepair.steps.map((step, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                        <Badge className={getStatusColor(step.status)}>
                          {step.status === 'pending' ? '待执行' :
                           step.status === 'running' ? '执行中' :
                           step.status === 'completed' ? '已完成' : '失败'}
                        </Badge>
                        <span className="text-sm">{step.order}. {step.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button onClick={() => setSelectedRepair(null)}>关闭</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* 创建修复弹窗 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建统一修复</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">修复名称</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="输入修复名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入修复描述"
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">修复类型</label>
                <Select value={formData.repairType} onValueChange={(value: any) => setFormData({ ...formData, repairType: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="script">脚本</SelectItem>
                    <SelectItem value="configuration">配置</SelectItem>
                    <SelectItem value="restart">重启</SelectItem>
                    <SelectItem value="rollback">回滚</SelectItem>
                    <SelectItem value="custom">自定义</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">优先级</label>
                <Select value={formData.priority} onValueChange={(value: any) => setFormData({ ...formData, priority: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">低</SelectItem>
                    <SelectItem value="medium">中</SelectItem>
                    <SelectItem value="high">高</SelectItem>
                    <SelectItem value="critical">严重</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">目标范围</label>
              <input
                type="text"
                value={formData.targetScope}
                onChange={(e) => setFormData({ ...formData, targetScope: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                placeholder="输入目标范围，如：server-1,server-2"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateRepair}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
