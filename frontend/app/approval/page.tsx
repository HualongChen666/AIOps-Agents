'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ApprovalList } from '@/components/ApprovalList';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle, Activity, AlertTriangle } from 'lucide-react';

interface HealthStatus {
  status: string;
  hitl_available: boolean;
}

export default function ApprovalPage() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [createForm, setCreateForm] = useState({
    title: '',
    workflow_id: 'default',
    steps: '[{"step_id":"step-1","name":"管理员审批","approver":"admin"}]',
    description: '',
  });
  const [queryForm, setQueryForm] = useState({
    request_id: '',
    step_id: '',
    approver: '',
    comment: '',
  });
  const [result, setResult] = useState<{ data: any; success: boolean } | null>(null);

  // 🔧 修复: 使用真实 API 获取健康状态
  const { data: healthData, refetch: _refetchHealth } = useQuery({
    queryKey: ['hitl-health'],
    queryFn: async () => {
      const resp = await api.get('/hitl/health');
      return resp.data;
    },
    refetchInterval: 30000, // 30秒刷新
  });

  useEffect(() => {
    if (healthData) {
      setHealthStatus(healthData);
    }
  }, [healthData]);

  const handleCreateRequest = async () => {
    try {
      const steps = JSON.parse(createForm.steps);
      const response = await api.post('/hitl/approval/request', {
        title: createForm.title || '审批请求',
        workflow_id: createForm.workflow_id || 'default',
        steps,
        description: createForm.description || '',
        context: {},
      });
      setResult({ data: response.data, success: true });
    } catch (error: any) {
      setResult({ data: error.response?.data || error.message, success: false });
    }
  };

  const handleQueryStatus = async () => {
    if (!queryForm.request_id) {
      setResult({ data: '请输入请求 ID', success: false });
      return;
    }
    try {
      const response = await api.get(`/hitl/approval/${queryForm.request_id}`);
      setResult({ data: response.data, success: true });
    } catch (error: any) {
      setResult({ data: error.response?.data || error.message, success: false });
    }
  };

  const handleApprove = async () => {
    if (!queryForm.request_id || !queryForm.step_id || !queryForm.approver) {
      setResult({ data: '请输入请求 ID、步骤 ID、审批人', success: false });
      return;
    }
    try {
      const params = new URLSearchParams({
        request_id: queryForm.request_id,
        step_id: queryForm.step_id,
        approver: queryForm.approver,
      });
      if (queryForm.comment) {
        params.append('comment', queryForm.comment);
      }
      const response = await api.post(`/hitl/approval/approve?${params.toString()}`);
      setResult({ data: response.data, success: true });
    } catch (error: any) {
      setResult({ data: error.response?.data || error.message, success: false });
    }
  };

  const handleReject = async () => {
    if (!queryForm.request_id || !queryForm.step_id || !queryForm.approver) {
      setResult({ data: '请输入请求 ID、步骤 ID、审批人', success: false });
      return;
    }
    try {
      const params = new URLSearchParams({
        request_id: queryForm.request_id,
        step_id: queryForm.step_id,
        approver: queryForm.approver,
      });
      if (queryForm.comment) {
        params.append('comment', queryForm.comment);
      }
      const response = await api.post(`/hitl/approval/reject?${params.toString()}`);
      setResult({ data: response.data, success: false });
    } catch (error: any) {
      setResult({ data: error.response?.data || error.message, success: false });
    }
  };

  const handleTakeover = async () => {
    if (!queryForm.request_id) {
      setResult({ data: '请输入请求 ID', success: false });
      return;
    }
    try {
      const response = await api.post(`/hitl/takeover/${queryForm.request_id}?reason=manual`);
      setResult({ data: response.data, success: true });
    } catch (error: any) {
      setResult({ data: error.response?.data || error.message, success: false });
    }
  };

  return (
    <main className="p-6 space-y-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            HITL 审批中心
          </h1>
          <p className="text-sm text-gray-500 mt-1">人工审批与接管工作流</p>
        </div>
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-gray-500" />
          <span className={`text-sm ${healthStatus?.hitl_available ? 'text-green-600' : 'text-red-600'}`}>
            {healthStatus?.status || '检查中...'} {healthStatus?.hitl_available ? '(可用)' : '(不可用)'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧表单区域 */}
        <div className="space-y-6">
          {/* 创建审批请求 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                创建审批请求
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                <Input
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  placeholder="修复方案审批"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">工作流 ID</label>
                <Input
                  value={createForm.workflow_id}
                  onChange={(e) => setCreateForm({ ...createForm, workflow_id: e.target.value })}
                  placeholder="default"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">审批步骤 (JSON 数组)</label>
                <Textarea
                  value={createForm.steps}
                  onChange={(e) => setCreateForm({ ...createForm, steps: e.target.value })}
                  placeholder='[{"step_id":"step-1","name":"管理员审批","approver":"admin"}]'
                  rows={4}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <Input
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  placeholder="审批描述（可选）"
                />
              </div>
              <Button onClick={handleCreateRequest} className="w-full">
                创建请求
              </Button>
            </CardContent>
          </Card>

          {/* 查询和操作 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                查询 / 操作
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">请求 ID</label>
                <Input
                  value={queryForm.request_id}
                  onChange={(e) => setQueryForm({ ...queryForm, request_id: e.target.value })}
                  placeholder="req-xxx"
                />
              </div>
              <Button onClick={handleQueryStatus} variant="outline" className="w-full">
                查询状态
              </Button>
              <div className="border-t pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">步骤 ID</label>
                  <Input
                    value={queryForm.step_id}
                    onChange={(e) => setQueryForm({ ...queryForm, step_id: e.target.value })}
                    placeholder="step-1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">审批人</label>
                  <Input
                    value={queryForm.approver}
                    onChange={(e) => setQueryForm({ ...queryForm, approver: e.target.value })}
                    placeholder="admin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">备注（可选）</label>
                  <Input
                    value={queryForm.comment}
                    onChange={(e) => setQueryForm({ ...queryForm, comment: e.target.value })}
                    placeholder="审批备注"
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleApprove} className="flex-1">
                    批准
                  </Button>
                  <Button onClick={handleReject} variant="destructive" className="flex-1">
                    拒绝
                  </Button>
                </div>
                <Button onClick={handleTakeover} variant="outline" className="w-full">
                  人工接管
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧结果区域 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>操作结果</CardTitle>
            </CardHeader>
            <CardContent>
              {result ? (
                <div className={`p-4 rounded-lg ${result.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} border`}>
                  <pre className="text-sm whitespace-pre-wrap overflow-auto max-h-96">
                    {typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">
                  在左侧创建或查询审批请求
                </div>
              )}
            </CardContent>
          </Card>

          {/* 审批列表 */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>待处理审批列表</CardTitle>
            </CardHeader>
            <CardContent>
              <ApprovalList />
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  );
}
