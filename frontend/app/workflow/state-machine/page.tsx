'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface StateTransition {
  from: string;
  to: string;
  event: string;
  action?: string;
}

interface StateMachine {
  id: string;
  name: string;
  description: string;
  initialState: string;
  states: string[];
  transitions: StateTransition[];
  currentState: string;
  createdAt: string;
  updatedAt: string;
}

export default function StateMachinePage() {
  const [stateMachines, setStateMachines] = useState<StateMachine[]>([]);
  const [selectedSM, setSelectedSM] = useState<StateMachine | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [transitionDialogOpen, setTransitionDialogOpen] = useState(false);
  const [editingSM, setEditingSM] = useState<StateMachine | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    initialState: '',
  });
  const [transitionForm, setTransitionForm] = useState({
    from: '',
    to: '',
    event: '',
    action: '',
  });

  const loadStateMachines = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<StateMachine[]>('/api/v1/state-machine');
      setStateMachines(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedSM(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载状态机失败');
      console.error('加载状态机失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStateMachines();
  }, []);

  const handleCreate = () => {
    setEditingSM(null);
    setFormData({ name: '', description: '', initialState: '' });
    setDialogOpen(true);
  };

  const handleEdit = (sm: StateMachine) => {
    setEditingSM(sm);
    setFormData({
      name: sm.name,
      description: sm.description,
      initialState: sm.initialState,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingSM) {
        await api.put(`/api/v1/state-machine/${editingSM.id}`, formData);
      } else {
        await api.post('/api/v1/state-machine', formData);
      }
      setDialogOpen(false);
      await loadStateMachines();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个状态机吗？')) return;
    try {
      await api.delete(`/api/v1/state-machine/${id}`);
      if (selectedSM?.id === id) {
        setSelectedSM(null);
      }
      await loadStateMachines();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleAddTransition = () => {
    setTransitionForm({ from: '', to: '', event: '', action: '' });
    setTransitionDialogOpen(true);
  };

  const handleSaveTransition = async () => {
    if (!selectedSM) return;
    try {
      await api.post(`/api/v1/state-machine/${selectedSM.id}/transitions`, transitionForm);
      setTransitionDialogOpen(false);
      await loadStateMachines();
    } catch (err: any) {
      setError(err.response?.data?.message || '添加转换失败');
      console.error('添加转换失败:', err);
    }
  };

  const handleDeleteTransition = async (index: number) => {
    if (!selectedSM) return;
    try {
      await api.delete(`/api/v1/state-machine/${selectedSM.id}/transitions/${index}`);
      await loadStateMachines();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除转换失败');
      console.error('删除转换失败:', err);
    }
  };

  const handleTriggerTransition = async (event: string) => {
    if (!selectedSM) return;
    try {
      await api.post(`/api/v1/state-machine/${selectedSM.id}/trigger`, { event });
      await loadStateMachines();
    } catch (err: any) {
      setError(err.response?.data?.message || '触发转换失败');
      console.error('触发转换失败:', err);
    }
  };

  const renderStateMachine = () => {
    if (!selectedSM) return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <h3 className="text-lg font-medium">当前状态</h3>
            <Badge variant="default" className="text-lg px-4 py-2 mt-2">
              {selectedSM.currentState}
            </Badge>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-medium">初始状态</h3>
            <Badge variant="outline" className="text-lg px-4 py-2 mt-2">
              {selectedSM.initialState}
            </Badge>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-3">状态转换图</h3>
          <div className="bg-white border rounded-lg p-6">
            <div className="flex flex-wrap gap-4 justify-center">
              {selectedSM.states.map((state, idx) => (
                <div
                  key={idx}
                  className={`px-4 py-2 rounded-lg border-2 ${
                    state === selectedSM.currentState
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 bg-gray-50'
                  }`}
                >
                  <div className="font-medium">{state}</div>
                  {state === selectedSM.initialState && (
                    <Badge variant="outline" className="mt-1 text-xs">初始</Badge>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-medium">转换规则</h3>
            <Button onClick={handleAddTransition}>添加转换</Button>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>从状态</TableHead>
                <TableHead>事件</TableHead>
                <TableHead>到状态</TableHead>
                <TableHead>动作</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {selectedSM.transitions.map((trans, idx) => (
                <TableRow key={idx}>
                  <TableCell className="font-medium">{trans.from}</TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTriggerTransition(trans.event)}
                    >
                      {trans.event}
                    </Button>
                  </TableCell>
                  <TableCell>{trans.to}</TableCell>
                  <TableCell className="text-gray-600">{trans.action || '-'}</TableCell>
                  <TableCell>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteTransition(idx)}
                    >
                      删除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {selectedSM.transitions.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-gray-500">
                    暂无转换规则
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">状态机</h1>
          <p className="text-gray-600 mt-1">定义和管理工作流状态机</p>
        </div>
        <Button onClick={handleCreate}>创建状态机</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>状态机列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : stateMachines.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无状态机</div>
            ) : (
              <div className="space-y-2">
                {stateMachines.map((sm) => (
                  <div
                    key={sm.id}
                    onClick={() => setSelectedSM(sm)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedSM?.id === sm.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{sm.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {sm.states.length} 状态 · {sm.transitions.length} 转换
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(sm); }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(sm.id); }}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>
              {selectedSM ? selectedSM.name : '选择状态机'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedSM ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  {selectedSM.description}
                </div>
                {renderStateMachine()}
              </div>
            ) : (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请从左侧选择一个状态机
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingSM ? '编辑状态机' : '创建状态机'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入状态机名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入状态机描述"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">初始状态</label>
              <Input
                value={formData.initialState}
                onChange={(e) => setFormData({ ...formData, initialState: e.target.value })}
                placeholder="输入初始状态"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name || !formData.initialState}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={transitionDialogOpen} onOpenChange={setTransitionDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>添加转换</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">从状态</label>
              <Input
                value={transitionForm.from}
                onChange={(e) => setTransitionForm({ ...transitionForm, from: e.target.value })}
                placeholder="输入源状态"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">事件</label>
              <Input
                value={transitionForm.event}
                onChange={(e) => setTransitionForm({ ...transitionForm, event: e.target.value })}
                placeholder="输入触发事件"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">到状态</label>
              <Input
                value={transitionForm.to}
                onChange={(e) => setTransitionForm({ ...transitionForm, to: e.target.value })}
                placeholder="输入目标状态"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">动作（可选）</label>
              <Input
                value={transitionForm.action}
                onChange={(e) => setTransitionForm({ ...transitionForm, action: e.target.value })}
                placeholder="输入执行动作"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTransitionDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveTransition} disabled={!transitionForm.from || !transitionForm.to || !transitionForm.event}>
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
