'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface ITSMIncident {
  incident_id: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  assigned_to: string | null;
  category: string;
  impact: string;
  urgency: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolution_notes: string | null;
}

interface ITSMProblem {
  problem_id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  root_cause: string | null;
  related_incidents: string[];
  workarounds: string[];
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

interface ITSMChange {
  change_id: string;
  title: string;
  description: string;
  change_type: string;
  status: string;
  priority: string;
  risk_level: string;
  planned_start: string;
  planned_end: string;
  requested_by: string;
  approved_by: string | null;
  created_at: string;
  updated_at: string;
  implemented_at: string | null;
}

interface ServiceCatalogItem {
  service_id: string;
  name: string;
  description: string;
  category: string;
  availability: string;
  sla_target: string;
  owner: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function ITSMAdvancedPage() {
  const [activeTab, setActiveTab] = useState<string>('incidents');
  const [incidents, setIncidents] = useState<ITSMIncident[]>([]);
  const [problems, setProblems] = useState<ITSMProblem[]>([]);
  const [changes, setChanges] = useState<ITSMChange[]>([]);
  const [services, setServices] = useState<ServiceCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newIncident, setNewIncident] = useState({
    title: '',
    description: '',
    priority: 'medium',
    category: '',
    impact: 'medium',
    urgency: 'medium',
    assigned_to: ''
  });

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'incidents') {
        const response = await api.get('/api/v1/itsm/incidents');
        setIncidents(response.data || []);
      } else if (activeTab === 'problems') {
        const response = await api.get('/api/v1/itsm/problems');
        setProblems(response.data || []);
      } else if (activeTab === 'services') {
        const response = await api.get('/api/v1/itsm/service-catalog');
        setServices(response.data || []);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateIncident = async () => {
    try {
      setError(null);
      await api.post('/api/v1/itsm/incidents', newIncident);
      setShowCreateForm(false);
      setNewIncident({
        title: '',
        description: '',
        priority: 'medium',
        category: '',
        impact: 'medium',
        urgency: 'medium',
        assigned_to: ''
      });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建工单失败');
    }
  };

  const handleUpdateIncident = async (incidentId: string, status: string) => {
    try {
      setError(null);
      await api.patch(`/api/v1/itsm/incidents/${incidentId}`, { status });
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新工单失败');
    }
  };

  const handleDeleteIncident = async (incidentId: string) => {
    if (!confirm('确定要删除此工单吗？')) return;

    try {
      setError(null);
      await api.delete(`/api/v1/itsm/incidents/${incidentId}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除工单失败');
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical': return 'destructive';
      case 'high': return 'destructive';
      case 'medium': return 'secondary';
      case 'low': return 'outline';
      default: return 'outline';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open': return 'default';
      case 'in_progress': return 'secondary';
      case 'resolved': return 'default';
      case 'closed': return 'outline';
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
        <h1 className="text-3xl font-bold text-gray-900">高级ITSM管理</h1>
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
          { id: 'incidents', name: '事件' },
          { id: 'problems', name: '问题' },
          { id: 'changes', name: '变更' },
          { id: 'services', name: '服务目录' },
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

      {/* 创建事件表单 */}
      {showCreateForm && activeTab === 'incidents' && (
        <Card>
          <CardHeader>
            <CardTitle>创建新事件</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
                <input
                  type="text"
                  value={newIncident.title}
                  onChange={(e) => setNewIncident({ ...newIncident, title: e.target.value })}
                  className="w-full border rounded-md p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={newIncident.description}
                  onChange={(e) => setNewIncident({ ...newIncident, description: e.target.value })}
                  className="w-full border rounded-md p-2 h-24"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
                  <select
                    value={newIncident.priority}
                    onChange={(e) => setNewIncident({ ...newIncident, priority: e.target.value })}
                    className="w-full border rounded-md p-2"
                  >
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                    <option value="critical">严重</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">类别</label>
                  <input
                    type="text"
                    value={newIncident.category}
                    onChange={(e) => setNewIncident({ ...newIncident, category: e.target.value })}
                    className="w-full border rounded-md p-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">影响</label>
                  <select
                    value={newIncident.impact}
                    onChange={(e) => setNewIncident({ ...newIncident, impact: e.target.value })}
                    className="w-full border rounded-md p-2"
                  >
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">紧急度</label>
                  <select
                    value={newIncident.urgency}
                    onChange={(e) => setNewIncident({ ...newIncident, urgency: e.target.value })}
                    className="w-full border rounded-md p-2"
                  >
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">分配给</label>
                <input
                  type="text"
                  value={newIncident.assigned_to}
                  onChange={(e) => setNewIncident({ ...newIncident, assigned_to: e.target.value })}
                  className="w-full border rounded-md p-2"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateIncident} className="flex-1">创建事件</Button>
                <Button onClick={() => setShowCreateForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 事件列表 */}
      {activeTab === 'incidents' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>事件 ({incidents.length})</CardTitle>
              <Button onClick={() => setShowCreateForm(!showCreateForm)}>
                {showCreateForm ? '取消' : '创建事件'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {incidents.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无事件</div>
            ) : (
              <div className="space-y-3">
                {incidents.map((incident) => (
                  <div key={incident.incident_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{incident.title}</h3>
                      <div className="flex gap-2">
                        <Badge variant={getPriorityColor(incident.priority)}>{incident.priority}</Badge>
                        <Badge variant={getStatusColor(incident.status)}>{incident.status}</Badge>
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">{incident.description}</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-500 mb-2">
                      <div>类别: {incident.category}</div>
                      <div>分配给: {incident.assigned_to || '未分配'}</div>
                      <div>影响: {incident.impact}</div>
                      <div>紧急度: {incident.urgency}</div>
                    </div>
                    <div className="text-xs text-gray-500 mb-3">
                      创建时间: {new Date(incident.created_at).toLocaleString()}
                      {incident.resolved_at && ` | 解决时间: ${new Date(incident.resolved_at).toLocaleString()}`}
                    </div>
                    <div className="flex gap-2">
                      {incident.status === 'open' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleUpdateIncident(incident.incident_id, 'in_progress')}
                        >
                          开始处理
                        </Button>
                      )}
                      {incident.status === 'in_progress' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleUpdateIncident(incident.incident_id, 'resolved')}
                        >
                          解决
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleDeleteIncident(incident.incident_id)}
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
      )}

      {/* 问题列表 */}
      {activeTab === 'problems' && (
        <Card>
          <CardHeader>
            <CardTitle>问题 ({problems.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {problems.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无问题</div>
            ) : (
              <div className="space-y-3">
                {problems.map((problem) => (
                  <div key={problem.problem_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{problem.title}</h3>
                      <Badge variant={getStatusColor(problem.status)}>{problem.status}</Badge>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">{problem.description}</div>
                    {problem.root_cause && (
                      <div className="text-sm text-gray-600 mb-2">
                        <span className="font-medium">根本原因:</span> {problem.root_cause}
                      </div>
                    )}
                    {problem.workarounds.length > 0 && (
                      <div className="mb-2">
                        <div className="text-sm font-medium text-gray-700 mb-1">变通方案:</div>
                        <ul className="text-sm text-gray-600 list-disc list-inside">
                          {problem.workarounds.map((workaround, i) => (
                            <li key={i}>{workaround}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      创建时间: {new Date(problem.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 服务目录 */}
      {activeTab === 'services' && (
        <Card>
          <CardHeader>
            <CardTitle>服务目录 ({services.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {services.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无服务</div>
            ) : (
              <div className="space-y-3">
                {services.map((service) => (
                  <div key={service.service_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">{service.name}</h3>
                      <Badge variant={service.status === 'active' ? 'default' : 'secondary'}>
                        {service.status}
                      </Badge>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">{service.description}</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600">
                      <div>类别: {service.category}</div>
                      <div>可用性: {service.availability}</div>
                      <div>SLA目标: {service.sla_target}</div>
                      <div>负责人: {service.owner}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 变更列表 */}
      {activeTab === 'changes' && (
        <Card>
          <CardHeader>
            <CardTitle>变更 ({changes.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {changes.length === 0 ? (
              <div className="text-gray-500 text-center py-8">暂无变更</div>
            ) : (
              <div className="text-gray-500 text-center py-8">变更功能开发中...</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
