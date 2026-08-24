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

interface DataSubject {
  id: string;
  name: string;
  email: string;
  type: 'customer' | 'employee' | 'partner' | 'other';
  dataCategories: string[];
  consentGiven: boolean;
  consentDate: string;
  lastAccessed: string;
}

interface DataRequest {
  id: string;
  subjectId: string;
  subjectName: string;
  type: 'access' | 'deletion' | 'correction' | 'portability';
  status: 'pending' | 'in_progress' | 'completed' | 'rejected';
  requestedAt: string;
  completedAt?: string;
  handler: string;
  notes: string;
}

interface PrivacyPolicy {
  id: string;
  name: string;
  version: string;
  effectiveDate: string;
  status: 'active' | 'draft' | 'archived';
  dataRetention: string;
  dataProcessing: string;
  userRights: string;
}

export default function DataPrivacyPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [subjects, setSubjects] = useState<DataSubject[]>([]);
  const [requests, setRequests] = useState<DataRequest[]>([]);
  const [policies, setPolicies] = useState<PrivacyPolicy[]>([]);
  const [activeTab, setActiveTab] = useState<'subjects' | 'requests' | 'policies'>('subjects');
  const [showAddSubjectModal, setShowAddSubjectModal] = useState(false);
  const [newSubject, setNewSubject] = useState({
    name: '',
    email: '',
    type: 'customer' as const,
    dataCategories: [] as string[],
  });

  const loadDataPrivacyData = async () => {
    setLoading(true);
    try {
      const [subjectsRes, requestsRes, policiesRes] = await Promise.all([
        api.get('/api/v1/security/data-privacy/subjects'),
        api.get('/api/v1/security/data-privacy/requests'),
        api.get('/api/v1/security/data-privacy/policies'),
      ]);

      const subjectsData = subjectsRes.data?.subjects || [];
      const requestsData = requestsRes.data?.requests || [];
      const policiesData = policiesRes.data?.policies || [];

      setSubjects(subjectsData);
      setRequests(requestsData);
      setPolicies(policiesData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddSubject = async () => {
    try {
      await api.post('/api/v1/security/data-privacy/subjects', newSubject);
      success('数据主体添加成功');
      setShowAddSubjectModal(false);
      setNewSubject({ name: '', email: '', type: 'customer', dataCategories: [] });
      loadDataPrivacyData();
    } catch (err) {
      showError('数据主体添加失败');
    }
  };

  const handleUpdateRequest = async (requestId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/data-privacy/requests/${requestId}`, { status });
      success('请求状态更新成功');
      loadDataPrivacyData();
    } catch (err) {
      showError('请求状态更新失败');
    }
  };

  const handleRevokeConsent = async (subjectId: string) => {
    try {
      await api.post(`/api/v1/security/data-privacy/subjects/${subjectId}/revoke-consent`);
      success('同意已撤销');
      loadDataPrivacyData();
    } catch (err) {
      showError('撤销同意失败');
    }
  };

  useEffect(() => {
    loadDataPrivacyData();
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
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
      case 'archived':
        return 'bg-red-100 text-red-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'customer':
        return 'bg-blue-100 text-blue-800';
      case 'employee':
        return 'bg-purple-100 text-purple-800';
      case 'partner':
        return 'bg-green-100 text-green-800';
      case 'other':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'subjects' as const, label: '数据主体' },
    { key: 'requests' as const, label: '数据请求' },
    { key: 'policies' as const, label: '隐私政策' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据隐私</h1>
        <div className="flex gap-2">
          <Button onClick={loadDataPrivacyData}>刷新数据</Button>
          <Button onClick={() => setShowAddSubjectModal(true)}>添加主体</Button>
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

      {/* 数据主体 */}
      {activeTab === 'subjects' && (
        <Card>
          <CardHeader>
            <CardTitle>数据主体</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>姓名</TableHead>
                  <TableHead>邮箱</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>数据类别</TableHead>
                  <TableHead>同意状态</TableHead>
                  <TableHead>同意日期</TableHead>
                  <TableHead>最后访问</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subjects.length > 0 ? subjects.map((subject) => (
                  <TableRow key={subject.id}>
                    <TableCell className="font-medium">{subject.name}</TableCell>
                    <TableCell>{subject.email}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(subject.type)}>{subject.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {subject.dataCategories.map((cat, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{cat}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={subject.consentGiven ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                        {subject.consentGiven ? '已同意' : '未同意'}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(subject.consentDate).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(subject.lastAccessed).toLocaleString()}</TableCell>
                    <TableCell>
                      {subject.consentGiven && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRevokeConsent(subject.id)}
                        >
                          撤销同意
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No data subjects found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 数据请求 */}
      {activeTab === 'requests' && (
        <Card>
          <CardHeader>
            <CardTitle>数据请求</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>主体</TableHead>
                  <TableHead>请求类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>请求时间</TableHead>
                  <TableHead>完成时间</TableHead>
                  <TableHead>处理人</TableHead>
                  <TableHead>备注</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.length > 0 ? requests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell className="font-medium">{request.subjectName}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{request.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(request.status)}>{request.status}</Badge>
                    </TableCell>
                    <TableCell>{new Date(request.requestedAt).toLocaleString()}</TableCell>
                    <TableCell>{request.completedAt ? new Date(request.completedAt).toLocaleString() : '-'}</TableCell>
                    <TableCell>{request.handler}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{request.notes}</TableCell>
                    <TableCell>
                      <Select
                        value={request.status}
                        onChange={(e) => handleUpdateRequest(request.id, e.target.value)}
                        className="w-32"
                      >
                        <option value="pending">待处理</option>
                        <option value="in_progress">处理中</option>
                        <option value="completed">已完成</option>
                        <option value="rejected">已拒绝</option>
                      </Select>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No data requests found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 隐私政策 */}
      {activeTab === 'policies' && (
        <Card>
          <CardHeader>
            <CardTitle>隐私政策</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>生效日期</TableHead>
                  <TableHead>数据保留</TableHead>
                  <TableHead>数据处理</TableHead>
                  <TableHead>用户权利</TableHead>
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.length > 0 ? policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell className="font-medium">{policy.name}</TableCell>
                    <TableCell>{policy.version}</TableCell>
                    <TableCell>{new Date(policy.effectiveDate).toLocaleDateString()}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{policy.dataRetention}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{policy.dataProcessing}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{policy.userRights}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(policy.status)}>{policy.status}</Badge>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No privacy policies found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 添加主体模态框 */}
      {showAddSubjectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加数据主体</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">姓名</label>
                <Input
                  value={newSubject.name}
                  onChange={(e) => setNewSubject({ ...newSubject, name: e.target.value })}
                  placeholder="输入姓名"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">邮箱</label>
                <Input
                  value={newSubject.email}
                  onChange={(e) => setNewSubject({ ...newSubject, email: e.target.value })}
                  placeholder="输入邮箱"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">类型</label>
                <Select
                  value={newSubject.type}
                  onChange={(e) => setNewSubject({ ...newSubject, type: e.target.value as any })}
                >
                  <option value="customer">客户</option>
                  <option value="employee">员工</option>
                  <option value="partner">合作伙伴</option>
                  <option value="other">其他</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">数据类别 (逗号分隔)</label>
                <Input
                  value={newSubject.dataCategories.join(',')}
                  onChange={(e) => setNewSubject({ ...newSubject, dataCategories: e.target.value.split(',').filter(c => c.trim()) })}
                  placeholder="个人信息,联系方式,支付信息"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddSubjectModal(false)}>取消</Button>
                <Button onClick={handleAddSubject}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
