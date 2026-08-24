'use client';

import { useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { Plus, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/useEnhancements';

interface IntegrationConfig {
  integration_type: string;
  name: string;
  endpoint: string;
  api_key?: string;
  config: Record<string, any>;
  enabled: boolean;
}

export default function IntegrationRegistrationPage() {
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState<IntegrationConfig>({
    integration_type: 'prometheus',
    name: '',
    endpoint: '',
    api_key: '',
    config: {},
    enabled: true,
  });

  const queryClient = useQueryClient();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const registrationMutation = useMutation({
    mutationFn: async (data: IntegrationConfig) => {
      const resp = await api.post('/api/v1/integration/register', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-list'] });
      setShowModal(false);
      setFormData({
        integration_type: 'prometheus',
        name: '',
        endpoint: '',
        api_key: '',
        config: {},
        enabled: true,
      });
      showSuccess('集成注册成功');
    },
    onError: (error: any) => {
      showError(error.response?.data?.message || '集成注册失败');
    },
  });

  const handleRegister = () => {
    if (!formData.name || !formData.endpoint) {
      showError('请填写必填字段');
      return;
    }
    registrationMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Plus className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">集成注册</h1>
            <p className="text-sm text-gray-500">注册新的外部系统集成</p>
          </div>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          注册新集成
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>快速注册</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { type: 'prometheus', name: 'Prometheus', icon: '📊' },
              { type: 'grafana', name: 'Grafana', icon: '📈' },
              { type: 'datadog', name: 'Datadog', icon: '🐕' },
              { type: 'elk', name: 'ELK Stack', icon: '📝' },
              { type: 'github', name: 'GitHub', icon: '🐙' },
              { type: 'jira', name: 'Jira', icon: '🎯' },
              { type: 'slack', name: 'Slack', icon: '💬' },
              { type: 'teams', name: 'Teams', icon: '👥' },
            ].map((item) => (
              <Button
                key={item.type}
                variant="outline"
                className="h-24 flex flex-col gap-2"
                onClick={() => {
                  setFormData({ ...formData, integration_type: item.type });
                  setShowModal(true);
                }}
              >
                <span className="text-2xl">{item.icon}</span>
                <span className="text-sm">{item.name}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <EnhancedModal
        open={showModal}
        onOpenChange={setShowModal}
        title="注册集成"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">集成类型</label>
            <select
              value={formData.integration_type}
              onChange={(e) => setFormData({ ...formData, integration_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="prometheus">Prometheus</option>
              <option value="grafana">Grafana</option>
              <option value="datadog">Datadog</option>
              <option value="elk">ELK Stack</option>
              <option value="github">GitHub</option>
              <option value="jira">Jira</option>
              <option value="slack">Slack</option>
              <option value="teams">Teams</option>
              <option value="servicenow">ServiceNow</option>
              <option value="kafka">Kafka</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="集成名称"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">端点URL</label>
            <Input
              value={formData.endpoint}
              onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
              placeholder="https://api.example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API密钥（可选）</label>
            <Input
              type="password"
              value={formData.api_key}
              onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
              placeholder="API密钥"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="rounded"
            />
            <label htmlFor="enabled" className="text-sm text-gray-700">启用集成</label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowModal(false)}>
              取消
            </Button>
            <Button 
              onClick={handleRegister} 
              disabled={registrationMutation.isPending}
            >
              {registrationMutation.isPending ? '注册中...' : '注册'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}
