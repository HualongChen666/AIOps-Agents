'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  test_type: string;
  framework: string;
  status: string;
  test_count: number;
  last_execution: string | null;
  last_result: string | null;
  schedule: string | null;
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface TestExecution {
  id: string;
  suite_id: string;
  suite_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration: number | null;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  coverage: number | null;
  triggered_by: string;
  trigger_type: string;
  logs_url: string | null;
  artifacts: string[];
}

export default function TestAutomationAdvancedPage() {
  const [activeTab, setActiveTab] = useState<string>('suites');
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateSuiteForm, setShowCreateSuiteForm] = useState(false);
  const [showCreateExecutionForm, setShowCreateExecutionForm] = useState(false);
  const [newSuite, setNewSuite] = useState({
    name: '',
    description: '',
    test_type: 'unit',
    framework: 'pytest',
    schedule: ''
  });
  const [newExecution, setNewExecution] = useState({
    suite_id: '',
    trigger_type: 'manual',
    environment: ''
  });

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'suites') {
        const response = await api.get('/api/v1/test-automation/suites');
        setSuites(response.data || []);
      } else if (activeTab === 'executions') {
        const response = await api.get('/api/v1/test-automation/executions');
        setExecutions(response.data || []);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSuite = async () => {
    try {
      setError(null);
      await api.post('/api/v1/test-automation/suites', newSuite);
      setShowCreateSuiteForm(false);
      setNewSuite({
        name: '',
        description: '',
        test_type: 'unit',
        framework: 'pytest',
        schedule: ''
      });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建测试套件失败');
    }
  };

  const handleCreateExecution = async () => {
    try {
      setError(null);
      await api.post('/api/v1/test-automation/executions', newExecution);
      setShowCreateExecutionForm(false);
      setNewExecution({
        suite_id: '',
        trigger_type: 'manual',
        environment: ''
      });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建执行记录失败');
    }
  };

  const handleDeleteSuite = async (suiteId: string) => {
    if (!confirm('确定要删除此测试套件吗？')) return;

    try {
      setError(null);
      await api.delete(`/api/v1/test-automation/suites/${suiteId}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除测试套件失败');
    }
  };

  const handleCancelExecution = async (executionId: string) => {
    if (!confirm('确定要取消此执行吗？')) return;

    try {
      setError(null);
      await api.post(`/api/v1/test-automation/executions/${executionId}/cancel`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '取消执行失败');
    }
  };

  const getSuiteStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active': return 'default';
      case 'inactive': return 'secondary';
      case 'archived': return 'outline';
      default: return 'outline';
    }
  };

  const getExecutionStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'default';
      case 'running': return 'secondary';
      case 'failed': return 'destructive';
      case 'cancelled': return 'outline';
      case 'pending': return 'outline';
      default: return 'outline';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级测试自动化</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 标签页 */}
      <div className="flex border-b">
        {[
          { id: 'suites', name: '测试套件' },
          { id: 'executions', name: '执行记录' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.name}
          </button>
        ))}
      </div>

      {/* 创建测试套件表单 */}
      {showCreateSuiteForm && activeTab === 'suites' && (
        <Card>
          <CardHeader>
            <CardTitle>创建测试套件</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">套件名称</label>
                <input
                  type="text"
                  value={newSuite.name}
                  onChange={(e) => setNewSuite({ ...newSuite, name: e.target.value })}
                  className="w-full border rounded-md p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={newSuite.description}
                  onChange={(e) => setNewSuite({ ...newSuite, description: e.target.value })}
                  className="w-full border rounded-md p-2 h-24"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">测试类型</label>
                  <select
                    value={newSuite.test_type}
                    onChange={(e) => setNewSuite({ ...newSuite, test_type: e.target.value })}
                    className="w-full border rounded-md p-2"
                  >
                    <option value="unit">单元测试</option>
                    <option value="integration">集成测试</option>
                    <option value="e2e">端到端测试</option>
                    <option value="performance">性能测试</option>
                    <option value="security">安全测试</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">框架</label>
                  <input
                    type="text"
                    value={newSuite.framework}
                    onChange={(e) => setNewSuite({ ...newSuite, framework: e.target.value })}
                    className="w-full border rounded-md p-2"
                    placeholder="pytest, jest, etc."
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">调度计划</label>
                <input
                  type="text"
                  value={newSuite.schedule}
                  onChange={(e) => setNewSuite({ ...newSuite, schedule: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="cron表达式，例如: 0 0 * * *"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateSuite} className="flex-1">创建套件</Button>
                <Button onClick={() => setShowCreateSuiteForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 创建执行记录表单 */}
      {showCreateExecutionForm && activeTab === 'executions' && (
        <Card>
          <CardHeader>
            <CardTitle>创建执行记录</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">测试套件</label>
                <select
                  value={newExecution.suite_id}
                  onChange={(e) => setNewExecution({ ...newExecution, suite_id: e.target.value })}
                  className="w-full border rounded-md p-2"
                >
                  <option value="">请选择测试套件</option>
                  {suites.map((suite) => (
                    <option key={suite.id} value={suite.id}>{suite.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">触发类型</label>
                  <select
                    value={newExecution.trigger_type}
                    onChange={(e) => setNewExecution({ ...newExecution, trigger_type: e.target.value })}
                    className="w-full border rounded-md p-2"
                  >
                    <option value="manual">手动</option>
                    <option value="scheduled">定时</option>
                    <option value="webhook">Webhook</option>
                    <option value="ci">CI/CD</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">环境</label>
                  <input
                    type="text"
                    value={newExecution.environment}
                    onChange={(e) => setNewExecution({ ...newExecution, environment: e.target.value })}
                    className="w-full border rounded-md p-2"
                    placeholder="dev, staging, production"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateExecution} className="flex-1">创建执行</Button>
                <Button onClick={() => setShowCreateExecutionForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 测试套件列表 */}
      {activeTab === 'suites' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>测试套件 ({suites.length})</CardTitle>
              <Button onClick={() => setShowCreateSuiteForm(!showCreateSuiteForm)}>
                {showCreateSuiteForm ? '取消' : '创建套件'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {suites.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无测试套件</div>
            ) : (
              <div className="space-y-3">
                {suites.map((suite) => (
                  <div key={suite.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{suite.name}</h3>
                      <div className="flex gap-2">
                        <Badge variant={getSuiteStatusColor(suite.status)}>{suite.status}</Badge>
                        <Badge variant="outline">{suite.test_type}</Badge>
                      </div>
                    </div>
                    {suite.description && (
                      <div className="text-sm text-gray-600 mb-2">{suite.description}</div>
                    )}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600 mb-2">
                      <div>框架: {suite.framework}</div>
                      <div>测试数: {suite.test_count}</div>
                      <div>创建者: {suite.created_by}</div>
                      {suite.schedule && <div>调度: {suite.schedule}</div>}
                    </div>
                    {suite.last_execution && (
                      <div className="text-xs text-gray-500 mb-2">
                        最后执行: {new Date(suite.last_execution).toLocaleString()}
                        {suite.last_result && ` | 结果: ${suite.last_result}`}
                      </div>
                    )}
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDeleteSuite(suite.id)}
                    >
                      删除
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 执行记录列表 */}
      {activeTab === 'executions' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>执行记录 ({executions.length})</CardTitle>
              <Button onClick={() => setShowCreateExecutionForm(!showCreateExecutionForm)}>
                {showCreateExecutionForm ? '取消' : '创建执行'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {executions.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无执行记录</div>
            ) : (
              <div className="space-y-3">
                {executions.map((execution) => (
                  <div key={execution.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{execution.suite_name}</h3>
                      <div className="flex gap-2">
                        <Badge variant={getExecutionStatusColor(execution.status)}>
                          {execution.status}
                        </Badge>
                        <Badge variant="outline">{execution.trigger_type}</Badge>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600 mb-2">
                      <div>总测试: {execution.total_tests}</div>
                      <div className="text-green-600">通过: {execution.passed_tests}</div>
                      <div className="text-red-600">失败: {execution.failed_tests}</div>
                      <div className="text-yellow-600">跳过: {execution.skipped_tests}</div>
                    </div>
                    {execution.duration && (
                      <div className="text-sm text-gray-600 mb-2">
                        执行时长: {execution.duration.toFixed(2)}秒
                      </div>
                    )}
                    {execution.coverage && (
                      <div className="text-sm text-gray-600 mb-2">
                        覆盖率: {(execution.coverage * 100).toFixed(1)}%
                      </div>
                    )}
                    <div className="text-xs text-gray-500 mb-2">
                      开始时间: {new Date(execution.started_at).toLocaleString()}
                      {execution.completed_at && ` | 完成时间: ${new Date(execution.completed_at).toLocaleString()}`}
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      触发者: {execution.triggered_by}
                    </div>
                    <div className="flex gap-2">
                      {(execution.status === 'pending' || execution.status === 'running') && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCancelExecution(execution.id)}
                        >
                          取消执行
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
