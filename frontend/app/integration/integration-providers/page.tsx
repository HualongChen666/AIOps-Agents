'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface IntegrationConfig {
  config_id: string;
  name: string;
  [key: string]: any;
}

export default function IntegrationProvidersPage() {
  const [activeTab, setActiveTab] = useState<string>('teams');
  const [configs, setConfigs] = useState<Record<string, IntegrationConfig[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newConfig, setNewConfig] = useState<Record<string, any>>({});

  const tabs = [
    { id: 'teams', name: 'Microsoft Teams', endpoint: '/teams/config' },
    { id: 'kafka', name: 'Kafka', endpoint: '/kafka/config' },
    { id: 'cloud', name: '云平台', endpoint: '/cloud/config' },
    { id: 'gitops', name: 'GitOps', endpoint: '/gitops/config' },
    { id: 'cicd', name: 'CI/CD', endpoint: '/cicd/config' },
    { id: 'itsm', name: 'ITSM', endpoint: '/itsm/config' },
    { id: 'oncall', name: 'Oncall', endpoint: '/oncall/config' },
    { id: 'slack', name: 'Slack', endpoint: '/slack/config' },
    { id: 'jira', name: 'Jira', endpoint: '/jira/config' },
    { id: 'servicenow', name: 'ServiceNow', endpoint: '/servicenow/config' },
  ];

  useEffect(() => {
    fetchConfigs();
  }, [activeTab]);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      setError(null);
      const tab = tabs.find(t => t.id === activeTab);
      if (!tab) return;

      const response = await api.get(`/api/v1/integration${tab.endpoint}`);
      setConfigs(prev => ({ ...prev, [activeTab]: response.data.configs || [] }));
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateConfig = async () => {
    try {
      setError(null);
      const tab = tabs.find(t => t.id === activeTab);
      if (!tab) return;

      await api.post(`/api/v1/integration${tab.endpoint}`, newConfig);
      setShowCreateForm(false);
      setNewConfig({});
      await fetchConfigs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建配置失败');
    }
  };

  const handleTestConnection = async (configId: string) => {
    try {
      setError(null);
      const tab = tabs.find(t => t.id === activeTab);
      if (!tab) return;

      const response = await api.post(`/api/v1/integration${tab.endpoint.replace('/config', `/test/${configId}`)}`);
      const result = response.data.test_result;
      alert(result.status === 'success' ? '连接测试成功' : `连接测试失败: ${result.message}`);
      await fetchConfigs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '测试连接失败');
    }
  };

  const getFormFields = () => {
    switch (activeTab) {
      case 'teams':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'tenant_id', label: '租户ID', type: 'text' },
          { name: 'client_id', label: '客户端ID', type: 'text' },
          { name: 'client_secret', label: '客户端密钥', type: 'password' },
        ];
      case 'kafka':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'bootstrap_servers', label: 'Bootstrap服务器', type: 'text' },
          { name: 'security_protocol', label: '安全协议', type: 'text', default: 'PLAINTEXT' },
        ];
      case 'cloud':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'provider', label: '提供商', type: 'select', options: ['aws', 'azure', 'gcp', 'alibaba'] },
          { name: 'region', label: '区域', type: 'text' },
          { name: 'access_key', label: '访问密钥', type: 'text' },
          { name: 'secret_key', label: '秘密密钥', type: 'password' },
        ];
      case 'gitops':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'gitops_type', label: 'GitOps类型', type: 'select', options: ['argocd', 'flux', 'jenkins-x'] },
          { name: 'url', label: '服务器URL', type: 'text' },
          { name: 'token', label: '认证令牌', type: 'password' },
        ];
      case 'cicd':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'cicd_type', label: 'CI/CD类型', type: 'select', options: ['jenkins', 'gitlab', 'circleci', 'github-actions'] },
          { name: 'url', label: '服务器URL', type: 'text' },
          { name: 'token', label: '认证令牌', type: 'password' },
        ];
      case 'itsm':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'itsm_type', label: 'ITSM类型', type: 'select', options: ['servicenow', 'bmc', 'cherwell'] },
          { name: 'url', label: '服务器URL', type: 'text' },
          { name: 'username', label: '用户名', type: 'text' },
          { name: 'password', label: '密码', type: 'password' },
        ];
      case 'oncall':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'provider', label: '提供商', type: 'select', options: ['pagerduty', 'opsgenie'] },
          { name: 'api_key', label: 'API密钥', type: 'password' },
        ];
      case 'slack':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'workspace', label: '工作空间', type: 'text' },
          { name: 'bot_token', label: 'Bot令牌', type: 'password' },
          { name: 'signing_secret', label: '签名密钥', type: 'password' },
        ];
      case 'jira':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'url', label: '服务器URL', type: 'text' },
          { name: 'username', label: '用户名', type: 'text' },
          { name: 'api_token', label: 'API令牌', type: 'password' },
        ];
      case 'servicenow':
        return [
          { name: 'name', label: '配置名称', type: 'text' },
          { name: 'instance_url', label: '实例URL', type: 'text' },
          { name: 'username', label: '用户名', type: 'text' },
          { name: 'password', label: '密码', type: 'password' },
        ];
      default:
        return [];
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
        <h1 className="text-3xl font-bold text-gray-900">集成提供商管理</h1>
        <Button onClick={fetchConfigs}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 标签页 */}
      <div className="flex border-b">
        {tabs.map((tab) => (
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

      {/* 创建配置表单 */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>创建新配置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {getFormFields().map((field) => (
                <div key={field.name}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{field.label}</label>
                  {field.type === 'select' ? (
                    <select
                      value={newConfig[field.name] || field.default || ''}
                      onChange={(e) => setNewConfig({ ...newConfig, [field.name]: e.target.value })}
                      className="w-full border rounded-md p-2"
                    >
                      <option value="">请选择</option>
                      {field.options?.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={field.type}
                      value={newConfig[field.name] || ''}
                      onChange={(e) => setNewConfig({ ...newConfig, [field.name]: e.target.value })}
                      className="w-full border rounded-md p-2"
                    />
                  )}
                </div>
              ))}
              <div className="flex gap-2">
                <Button onClick={handleCreateConfig} className="flex-1">创建配置</Button>
                <Button onClick={() => setShowCreateForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 配置列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{tabs.find(t => t.id === activeTab)?.name} 配置 ({configs[activeTab]?.length || 0})</CardTitle>
            <Button onClick={() => setShowCreateForm(!showCreateForm)}>
              {showCreateForm ? '取消' : '创建配置'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!configs[activeTab] || configs[activeTab].length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无配置</div>
          ) : (
            <div className="space-y-3">
              {configs[activeTab].map((config) => (
                <div key={config.config_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{config.name}</h3>
                    <div className="flex gap-2">
                      <Badge variant={config.enabled ? 'default' : 'secondary'}>
                        {config.enabled ? '已启用' : '已禁用'}
                      </Badge>
                      <Badge variant={config.status === 'connected' ? 'default' : 'destructive'}>
                        {config.status || '未知'}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">
                    ID: {config.config_id}
                    {config.last_sync && ` | 最后同步: ${new Date(config.last_sync).toLocaleString()}`}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleTestConnection(config.config_id)}
                    >
                      测试连接
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
