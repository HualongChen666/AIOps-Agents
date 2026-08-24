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

interface CompliancePolicy {
  id: string;
  name: string;
  standard: string;
  category: string;
  description: string;
  status: 'active' | 'draft' | 'archived';
  version: string;
  effectiveDate: string;
  reviewDate: string;
  owner: string;
}

interface ComplianceTask {
  id: string;
  policyId: string;
  policyName: string;
  title: string;
  description: string;
  assignee: string;
  dueDate: string;
  status: 'pending' | 'in_progress' | 'completed' | 'overdue';
  priority: 'critical' | 'high' | 'medium' | 'low';
}

interface ComplianceEvidence {
  id: string;
  policyId: string;
  policyName: string;
  type: 'document' | 'screenshot' | 'log' | 'report';
  title: string;
  uploadedBy: string;
  uploadedAt: string;
  status: 'approved' | 'pending' | 'rejected';
}

export default function ComplianceManagementPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [policies, setPolicies] = useState<CompliancePolicy[]>([]);
  const [tasks, setTasks] = useState<ComplianceTask[]>([]);
  const [evidence, setEvidence] = useState<ComplianceEvidence[]>([]);
  const [activeTab, setActiveTab] = useState<'policies' | 'tasks' | 'evidence'>('policies');
  const [showAddPolicyModal, setShowAddPolicyModal] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    name: '',
    standard: '',
    category: '',
    description: '',
    version: '1.0',
    effectiveDate: '',
    reviewDate: '',
    owner: '',
  });

  const loadComplianceManagementData = async () => {
    setLoading(true);
    try {
      const [policiesRes, tasksRes, evidenceRes] = await Promise.all([
        api.get('/api/v1/security/compliance-management/policies'),
        api.get('/api/v1/security/compliance-management/tasks'),
        api.get('/api/v1/security/compliance-management/evidence'),
      ]);

      const policiesData = policiesRes.data?.policies || [];
      const tasksData = tasksRes.data?.tasks || [];
      const evidenceData = evidenceRes.data?.evidence || [];

      setPolicies(policiesData);
      setTasks(tasksData);
      setEvidence(evidenceData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddPolicy = async () => {
    try {
      await api.post('/api/v1/security/compliance-management/policies', newPolicy);
      success('合规策略添加成功');
      setShowAddPolicyModal(false);
      setNewPolicy({
        name: '',
        standard: '',
        category: '',
        description: '',
        version: '1.0',
        effectiveDate: '',
        reviewDate: '',
        owner: '',
      });
      loadComplianceManagementData();
    } catch (err) {
      showError('策略添加失败');
    }
  };

  const handleUpdateTaskStatus = async (taskId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/compliance-management/tasks/${taskId}`, { status });
      success('任务状态更新成功');
      loadComplianceManagementData();
    } catch (err) {
      showError('任务状态更新失败');
    }
  };

  const handleApproveEvidence = async (evidenceId: string) => {
    try {
      await api.patch(`/api/v1/security/compliance-management/evidence/${evidenceId}`, {
        status: 'approved',
      });
      success('证据已批准');
      loadComplianceManagementData();
    } catch (err) {
      showError('证据批准失败');
    }
  };

  useEffect(() => {
    loadComplianceManagementData();
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
      case 'active':
      case 'completed':
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'draft':
      case 'pending':
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'archived':
      case 'rejected':
        return 'bg-gray-100 text-gray-800';
      case 'overdue':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'policies' as const, label: '合规策略' },
    { key: 'tasks' as const, label: '合规任务' },
    { key: 'evidence' as const, label: '合规证据' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">合规管理</h1>
        <div className="flex gap-2">
          <Button onClick={loadComplianceManagementData}>刷新数据</Button>
          <Button onClick={() => setShowAddPolicyModal(true)}>添加策略</Button>
        </div>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 合规策略 */}
      {activeTab === 'policies' && (
        <Card>
          <CardHeader>
            <CardTitle>合规策略</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>标准</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>负责人</TableHead>
                  <TableHead>生效日期</TableHead>
                  <TableHead>审查日期</TableHead>
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.length > 0 ? policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell className="font-medium">{policy.name}</TableCell>
                    <TableCell>{policy.standard}</TableCell>
                    <TableCell>{policy.category}</TableCell>
                    <TableCell>{policy.version}</TableCell>
                    <TableCell>{policy.owner}</TableCell>
                    <TableCell>{new Date(policy.effectiveDate).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(policy.reviewDate).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(policy.status)}>{policy.status}</Badge>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No compliance policies found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 合规任务 */}
      {activeTab === 'tasks' && (
        <Card>
          <CardHeader>
            <CardTitle>合规任务</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>策略</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>负责人</TableHead>
                  <TableHead>截止日期</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.length > 0 ? tasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell>{task.policyName}</TableCell>
                    <TableCell className="font-medium">{task.title}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{task.description}</TableCell>
                    <TableCell>{task.assignee}</TableCell>
                    <TableCell>{new Date(task.dueDate).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge className={getPriorityColor(task.priority)}>{task.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(task.status)}>{task.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={task.status}
                        onChange={(e) => handleUpdateTaskStatus(task.id, e.target.value)}
                        className="w-32"
                      >
                        <option value="pending">待处理</option>
                        <option value="in_progress">进行中</option>
                        <option value="completed">已完成</option>
                      </Select>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No compliance tasks found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 合规证据 */}
      {activeTab === 'evidence' && (
        <Card>
          <CardHeader>
            <CardTitle>合规证据</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>策略</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead>上传者</TableHead>
                  <TableHead>上传时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {evidence.length > 0 ? evidence.map((ev) => (
                  <TableRow key={ev.id}>
                    <TableCell>{ev.policyName}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{ev.type}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{ev.title}</TableCell>
                    <TableCell>{ev.uploadedBy}</TableCell>
                    <TableCell>{new Date(ev.uploadedAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(ev.status)}>{ev.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {ev.status === 'pending' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleApproveEvidence(ev.id)}
                        >
                          批准
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No compliance evidence found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 添加策略模态框 */}
      {showAddPolicyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加合规策略</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">策略名称</label>
                <Input
                  value={newPolicy.name}
                  onChange={(e) => setNewPolicy({ ...newPolicy, name: e.target.value })}
                  placeholder="输入策略名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">合规标准</label>
                <Input
                  value={newPolicy.standard}
                  onChange={(e) => setNewPolicy({ ...newPolicy, standard: e.target.value })}
                  placeholder="例如: ISO27001, PCI-DSS"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">分类</label>
                <Input
                  value={newPolicy.category}
                  onChange={(e) => setNewPolicy({ ...newPolicy, category: e.target.value })}
                  placeholder="策略分类"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">描述</label>
                <Input
                  value={newPolicy.description}
                  onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
                  placeholder="策略描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">版本</label>
                <Input
                  value={newPolicy.version}
                  onChange={(e) => setNewPolicy({ ...newPolicy, version: e.target.value })}
                  placeholder="1.0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">负责人</label>
                <Input
                  value={newPolicy.owner}
                  onChange={(e) => setNewPolicy({ ...newPolicy, owner: e.target.value })}
                  placeholder="负责人"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">生效日期</label>
                  <Input
                    type="date"
                    value={newPolicy.effectiveDate}
                    onChange={(e) => setNewPolicy({ ...newPolicy, effectiveDate: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">审查日期</label>
                  <Input
                    type="date"
                    value={newPolicy.reviewDate}
                    onChange={(e) => setNewPolicy({ ...newPolicy, reviewDate: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddPolicyModal(false)}>取消</Button>
                <Button onClick={handleAddPolicy}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
