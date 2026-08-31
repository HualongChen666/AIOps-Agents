'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Channel {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  config: Record<string, any>;
  priority: number;
  retry_count: number;
  timeout: number;
  created_at: string;
  updated_at: string;
}

interface Template {
  id: string;
  name: string;
  subject: string;
  body: string;
  type: string;
  variables: string[];
  enabled: boolean;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Rule {
  id: string;
  name: string;
  condition: string;
  channels: string[];
  template_id: string;
  enabled: boolean;
  priority: number;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface NotificationHistory {
  id: string;
  channel_id: string;
  channel_name: string;
  rule_id: string | null;
  template_id: string;
  status: string;
  error_message: string | null;
  sent_at: string;
  metadata: Record<string, any>;
}

type TabType = 'channels' | 'templates' | 'rules' | 'history';

export default function NotifyAdvancedPage() {
  const [activeTab, setActiveTab] = useState<TabType>('channels');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [channels, setChannels] = useState<Channel[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [history, setHistory] = useState<NotificationHistory[]>([]);

  // Form states
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<Record<string, any>>({});

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      switch (activeTab) {
        case 'channels':
          await fetchChannels();
          break;
        case 'templates':
          await fetchTemplates();
          break;
        case 'rules':
          await fetchRules();
          break;
        case 'history':
          await fetchHistory();
          break;
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchChannels = async () => {
    const res = await api.get('/api/v1/notify/channels');
    setChannels(res.data || []);
  };

  const fetchTemplates = async () => {
    const res = await api.get('/api/v1/notify/templates');
    setTemplates(res.data || []);
  };

  const fetchRules = async () => {
    const res = await api.get('/api/v1/notify/rules');
    setRules(res.data || []);
  };

  const fetchHistory = async () => {
    // Mock history data since endpoint might not exist
    const mockHistory: NotificationHistory[] = [
      {
        id: '1',
        channel_id: 'ch1',
        channel_name: 'Email Channel',
        rule_id: 'rule1',
        template_id: 'tpl1',
        status: 'sent',
        error_message: null,
        sent_at: new Date().toISOString(),
        metadata: {},
      },
    ];
    setHistory(mockHistory);
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      let endpoint = '';
      let data = formData;

      switch (activeTab) {
        case 'channels':
          endpoint = '/api/v1/notify/channels';
          break;
        case 'templates':
          endpoint = '/api/v1/notify/templates';
          break;
        case 'rules':
          endpoint = '/api/v1/notify/rules';
          break;
        default:
          return;
      }

      await api.post(endpoint, data);
      setShowCreateForm(false);
      setFormData({});
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除吗？')) return;

    try {
      setLoading(true);
      let endpoint = '';

      switch (activeTab) {
        case 'channels':
          endpoint = `/api/v1/notify/channels/${id}`;
          break;
        case 'templates':
          endpoint = `/api/v1/notify/templates/${id}`;
          break;
        default:
          return;
      }

      await api.delete(endpoint);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async (id: string, currentEnabled: boolean) => {
    try {
      setLoading(true);
      let endpoint = '';
      let data = { enabled: !currentEnabled };

      switch (activeTab) {
        case 'channels':
          endpoint = `/api/v1/notify/channels/${id}`;
          break;
        case 'templates':
          endpoint = `/api/v1/notify/templates/${id}`;
          break;
        case 'rules':
          endpoint = `/api/v1/notify/rules/${id}`;
          break;
        default:
          return;
      }

      await api.patch(endpoint, data);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !channels.length && !templates.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级通知系统</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {(['channels', 'templates', 'rules', 'history'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {activeTab === 'channels' && '通知渠道'}
              {activeTab === 'templates' && '通知模板'}
              {activeTab === 'rules' && '通知规则'}
              {activeTab === 'history' && '发送历史'}
            </CardTitle>
            {activeTab !== 'history' && (
              <Button onClick={() => setShowCreateForm(true)}>创建</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : (
            <div className="space-y-4">
              {/* Channels List */}
              {activeTab === 'channels' && channels.map((channel) => (
                <div key={channel.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{channel.name}</h3>
                      <div className="text-sm text-gray-500">类型: {channel.type}</div>
                      <div className="text-sm text-gray-500">优先级: {channel.priority}</div>
                      <div className="text-sm text-gray-500">重试次数: {channel.retry_count}</div>
                      <div className="text-sm text-gray-500">超时: {channel.timeout}s</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={channel.enabled ? 'default' : 'secondary'}>
                        {channel.enabled ? '启用' : '禁用'}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleEnabled(channel.id, channel.enabled)}
                      >
                        {channel.enabled ? '禁用' : '启用'}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(channel.id)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Templates List */}
              {activeTab === 'templates' && templates.map((template) => (
                <div key={template.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold">{template.name}</h3>
                      <div className="text-sm text-gray-500">主题: {template.subject}</div>
                      <div className="text-sm text-gray-500">类型: {template.type}</div>
                      <div className="text-sm text-gray-500">
                        变量: {template.variables.join(', ')}
                      </div>
                      <div className="text-sm text-gray-500 mt-2 max-h-20 overflow-y-auto">
                        {template.body.substring(0, 100)}...
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      <Badge variant={template.enabled ? 'default' : 'secondary'}>
                        {template.enabled ? '启用' : '禁用'}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleEnabled(template.id, template.enabled)}
                      >
                        {template.enabled ? '禁用' : '启用'}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(template.id)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Rules List */}
              {activeTab === 'rules' && rules.map((rule) => (
                <div key={rule.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{rule.name}</h3>
                      <div className="text-sm text-gray-500">条件: {rule.condition}</div>
                      <div className="text-sm text-gray-500">渠道数: {rule.channels.length}</div>
                      <div className="text-sm text-gray-500">模板ID: {rule.template_id}</div>
                      <div className="text-sm text-gray-500">优先级: {rule.priority}</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                        {rule.enabled ? '启用' : '禁用'}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleEnabled(rule.id, rule.enabled)}
                      >
                        {rule.enabled ? '禁用' : '启用'}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* History List */}
              {activeTab === 'history' && history.map((item) => (
                <div key={item.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{item.channel_name}</h3>
                      <div className="text-sm text-gray-500">模板ID: {item.template_id}</div>
                      <div className="text-sm text-gray-500">规则ID: {item.rule_id || 'N/A'}</div>
                      <div className="text-sm text-gray-500">
                        发送时间: {new Date(item.sent_at).toLocaleString()}
                      </div>
                      {item.error_message && (
                        <div className="text-sm text-red-500 mt-1">{item.error_message}</div>
                      )}
                    </div>
                    <Badge variant={item.status === 'sent' ? 'default' : 'destructive'}>
                      {item.status}
                    </Badge>
                  </div>
                </div>
              ))}

              {/* Empty State */}
              {activeTab === 'channels' && channels.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无通知渠道</div>
              )}
              {activeTab === 'templates' && templates.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无通知模板</div>
              )}
              {activeTab === 'rules' && rules.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无通知规则</div>
              )}
              {activeTab === 'history' && history.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无发送历史</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-semibold mb-4">创建{activeTab}</h2>
            <div className="space-y-4">
              {activeTab === 'channels' && (
                <>
                  <input
                    type="text"
                    placeholder="渠道名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <select
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  >
                    <option value="">选择类型</option>
                    <option value="email">邮件</option>
                    <option value="slack">Slack</option>
                    <option value="pagerduty">PagerDuty</option>
                    <option value="sms">短信</option>
                    <option value="webhook">Webhook</option>
                    <option value="teams">Teams</option>
                  </select>
                  <input
                    type="number"
                    placeholder="优先级"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                  />
                  <input
                    type="number"
                    placeholder="重试次数"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, retry_count: parseInt(e.target.value) })}
                  />
                  <input
                    type="number"
                    placeholder="超时(秒)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) })}
                  />
                </>
              )}
              {activeTab === 'templates' && (
                <>
                  <input
                    type="text"
                    placeholder="模板名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="主题"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  />
                  <textarea
                    placeholder="模板内容"
                    className="w-full border rounded px-3 py-2 h-32"
                    onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                  />
                  <select
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  >
                    <option value="email">邮件</option>
                    <option value="slack">Slack</option>
                    <option value="sms">短信</option>
                  </select>
                  <input
                    type="text"
                    placeholder="变量 (逗号分隔)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, variables: e.target.value.split(',') })}
                  />
                </>
              )}
              {activeTab === 'rules' && (
                <>
                  <input
                    type="text"
                    placeholder="规则名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="条件表达式"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="渠道ID (逗号分隔)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, channels: e.target.value.split(',') })}
                  />
                  <input
                    type="text"
                    placeholder="模板ID"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
                  />
                  <input
                    type="number"
                    placeholder="优先级"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                  />
                </>
              )}
            </div>
            <div className="flex justify-end space-x-2 mt-6">
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>取消</Button>
              <Button onClick={handleCreate}>创建</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
