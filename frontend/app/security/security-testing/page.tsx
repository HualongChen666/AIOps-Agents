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

interface SecurityTest {
  id: string;
  name: string;
  testType: 'sast' | 'dast' | 'dependency' | 'container' | 'infrastructure';
  target: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startedAt: string;
  completedAt?: string;
  findings: number;
  criticalFindings: number;
  highFindings: number;
  mediumFindings: number;
  lowFindings: number;
}

interface TestSuite {
  id: string;
  name: string;
  description: string;
  testCount: number;
  lastRun: string;
  enabled: boolean;
}

interface TestResult {
  id: string;
  testId: string;
  testName: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'pass' | 'fail' | 'warning';
  description: string;
  recommendation: string;
  timestamp: string;
}

export default function SecurityTestingPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [tests, setTests] = useState<SecurityTest[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [results, setResults] = useState<TestResult[]>([]);
  const [activeTab, setActiveTab] = useState<'tests' | 'suites' | 'results'>('tests');
  const [showNewTestModal, setShowNewTestModal] = useState(false);
  const [newTest, setNewTest] = useState({
    name: '',
    testType: 'sast' as const,
    target: '',
  });

  const loadSecurityTestData = async () => {
    setLoading(true);
    try {
      const [testsRes, suitesRes, resultsRes] = await Promise.all([
        api.get('/api/v1/security/security-testing/tests'),
        api.get('/api/v1/security/security-testing/suites'),
        api.get('/api/v1/security/security-testing/results'),
      ]);

      const testsData = testsRes.data?.tests || [];
      const suitesData = suitesRes.data?.suites || [];
      const resultsData = resultsRes.data?.results || [];

      setTests(testsData);
      setSuites(suitesData);
      setResults(resultsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleStartTest = async () => {
    try {
      await api.post('/api/v1/security/security-testing/tests/start', newTest);
      success('安全测试已启动');
      setShowNewTestModal(false);
      setNewTest({ name: '', testType: 'sast', target: '' });
      loadSecurityTestData();
    } catch (err) {
      showError('启动测试失败');
    }
  };

  const handleRunSuite = async (suiteId: string) => {
    try {
      await api.post(`/api/v1/security/security-testing/suites/${suiteId}/run`);
      success('测试套件已启动');
      loadSecurityTestData();
    } catch (err) {
      showError('启动套件失败');
    }
  };

  const handleToggleSuite = async (suiteId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/security-testing/suites/${suiteId}`, { enabled });
      success('套件状态更新成功');
      loadSecurityTestData();
    } catch (err) {
      showError('状态更新失败');
    }
  };

  useEffect(() => {
    loadSecurityTestData();
    // Auto-refresh for running tests
    const interval = setInterval(() => {
      const hasRunningTests = tests.some(t => t.status === 'running');
      if (hasRunningTests) {
        loadSecurityTestData();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [tests]);

  if (isLoading && !tests.length) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error && !tests.length) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      case 'info':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getResultStatusColor = (status: string) => {
    switch (status) {
      case 'pass':
        return 'bg-green-100 text-green-800';
      case 'fail':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'tests' as const, label: '安全测试' },
    { key: 'suites' as const, label: '测试套件' },
    { key: 'results' as const, label: '测试结果' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">安全测试</h1>
        <div className="flex gap-2">
          <Button onClick={loadSecurityTestData}>刷新数据</Button>
          <Button onClick={() => setShowNewTestModal(true)}>新建测试</Button>
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

      {/* 安全测试 */}
      {activeTab === 'tests' && (
        <Card>
          <CardHeader>
            <CardTitle>安全测试</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>目标</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>进度</TableHead>
                  <TableHead>发现</TableHead>
                  <TableHead>严重</TableHead>
                  <TableHead>高</TableHead>
                  <TableHead>中</TableHead>
                  <TableHead>低</TableHead>
                  <TableHead>开始时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tests.length > 0 ? tests.map((test) => (
                  <TableRow key={test.id}>
                    <TableCell className="font-medium">{test.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{test.testType.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{test.target}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(test.status)}>{test.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${test.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-sm">{test.progress}%</span>
                    </TableCell>
                    <TableCell>{test.findings}</TableCell>
                    <TableCell className="text-red-600 font-bold">{test.criticalFindings}</TableCell>
                    <TableCell className="text-orange-600">{test.highFindings}</TableCell>
                    <TableCell className="text-yellow-600">{test.mediumFindings}</TableCell>
                    <TableCell className="text-blue-600">{test.lowFindings}</TableCell>
                    <TableCell>{new Date(test.startedAt).toLocaleString()}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center text-gray-500">
                      No security tests found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 测试套件 */}
      {activeTab === 'suites' && (
        <Card>
          <CardHeader>
            <CardTitle>测试套件</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>测试数量</TableHead>
                  <TableHead>最后运行</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {suites.length > 0 ? suites.map((suite) => (
                  <TableRow key={suite.id}>
                    <TableCell className="font-medium">{suite.name}</TableCell>
                    <TableCell>{suite.description}</TableCell>
                    <TableCell>{suite.testCount}</TableCell>
                    <TableCell>{new Date(suite.lastRun).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={suite.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {suite.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRunSuite(suite.id)}
                          disabled={!suite.enabled}
                        >
                          运行
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleSuite(suite.id, !suite.enabled)}
                        >
                          {suite.enabled ? '禁用' : '启用'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-gray-500">
                      No test suites found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 测试结果 */}
      {activeTab === 'results' && (
        <Card>
          <CardHeader>
            <CardTitle>测试结果</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>测试名称</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>严重性</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>建议</TableHead>
                  <TableHead>时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.length > 0 ? results.map((result) => (
                  <TableRow key={result.id}>
                    <TableCell className="font-medium">{result.testName}</TableCell>
                    <TableCell>{result.category}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(result.severity)}>{result.severity}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getResultStatusColor(result.status)}>{result.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{result.description}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{result.recommendation}</TableCell>
                    <TableCell>{new Date(result.timestamp).toLocaleString()}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No test results found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 新建测试模态框 */}
      {showNewTestModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>新建安全测试</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">测试名称</label>
                <Input
                  value={newTest.name}
                  onChange={(e) => setNewTest({ ...newTest, name: e.target.value })}
                  placeholder="输入测试名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">测试类型</label>
                <Select
                  value={newTest.testType}
                  onChange={(e) => setNewTest({ ...newTest, testType: e.target.value as any })}
                >
                  <option value="sast">静态应用安全测试 (SAST)</option>
                  <option value="dast">动态应用安全测试 (DAST)</option>
                  <option value="dependency">依赖扫描</option>
                  <option value="container">容器扫描</option>
                  <option value="infrastructure">基础设施扫描</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">测试目标</label>
                <Input
                  value={newTest.target}
                  onChange={(e) => setNewTest({ ...newTest, target: e.target.value })}
                  placeholder="输入目标URL、代码路径或镜像名称"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowNewTestModal(false)}>取消</Button>
                <Button onClick={handleStartTest}>启动</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
