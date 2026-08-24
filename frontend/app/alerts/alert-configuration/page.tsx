'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Settings, RefreshCw, Save, Bell, Activity } from 'lucide-react';

interface AlertConfig {
  enabled: boolean;
  default_severity: string;
  auto_resolve_timeout: number;
  max_alerts_per_source: number;
  enable_intelligent_analysis: boolean;
  enable_prediction: boolean;
  enable_correlation: boolean;
  retention_days: number;
  notification_cooldown: number;
  escalation_enabled: boolean;
  suppression_enabled: boolean;
}

export default function AlertConfigurationPage() {
  const [config, setConfig] = useState<AlertConfig>({
    enabled: true,
    default_severity: 'medium',
    auto_resolve_timeout: 3600,
    max_alerts_per_source: 1000,
    enable_intelligent_analysis: true,
    enable_prediction: false,
    enable_correlation: true,
    retention_days: 30,
    notification_cooldown: 300,
    escalation_enabled: true,
    suppression_enabled: true,
  });

  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, isLoading: configLoading, error: configError, refetch: refetchConfig } = useQuery<AlertConfig>({
    queryKey: ['alert-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/configuration');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const saveConfigMutation = useMutation({
    mutationFn: async (data: AlertConfig) => {
      const resp = await api.put('/api/v1/alerts/configuration', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('配置保存成功');
      queryClient.invalidateQueries({ queryKey: ['alert-config'] });
    },
    onError: () => showError('保存配置失败'),
  });

  useEffect(() => {
    if (configData) {
      setConfig(configData);
    }
  }, [configData]);

  useEffect(() => {
    if (configError) showError('Failed to load alert configuration');
  }, [configError, showError]);

  const handleSave = () => {
    saveConfigMutation.mutate(config);
  };

  if (configLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警配置</h1>
            <p className="text-sm text-gray-500">全局告警系统配置</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleSave} disabled={saveConfigMutation.isPending}>
            <Save className="h-4 w-4 mr-2" />
            保存配置
          </Button>
          <Button onClick={() => refetchConfig()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>基本配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用告警系统</label>
                <Select
                  value={config.enabled ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, enabled: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">默认严重度</label>
                <Select
                  value={config.default_severity}
                  onChange={(e) => setConfig({ ...config, default_severity: e.target.value })}
                >
                  <option value="critical">严重</option>
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">自动解决超时(秒)</label>
                <Input
                  type="number"
                  value={config.auto_resolve_timeout}
                  onChange={(e) => setConfig({ ...config, auto_resolve_timeout: parseInt(e.target.value) || 3600 })}
                  placeholder="3600"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">每个源最大告警数</label>
                <Input
                  type="number"
                  value={config.max_alerts_per_source}
                  onChange={(e) => setConfig({ ...config, max_alerts_per_source: parseInt(e.target.value) || 1000 })}
                  placeholder="1000"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">数据保留天数</label>
                <Input
                  type="number"
                  value={config.retention_days}
                  onChange={(e) => setConfig({ ...config, retention_days: parseInt(e.target.value) || 30 })}
                  placeholder="30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">通知冷却时间(秒)</label>
                <Input
                  type="number"
                  value={config.notification_cooldown}
                  onChange={(e) => setConfig({ ...config, notification_cooldown: parseInt(e.target.value) || 300 })}
                  placeholder="300"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            智能功能
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用智能分析</label>
                <Select
                  value={config.enable_intelligent_analysis ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, enable_intelligent_analysis: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用告警预测</label>
                <Select
                  value={config.enable_prediction ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, enable_prediction: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用告警关联</label>
                <Select
                  value={config.enable_correlation ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, enable_correlation: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            高级功能
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用告警升级</label>
                <Select
                  value={config.escalation_enabled ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, escalation_enabled: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">启用告警抑制</label>
                <Select
                  value={config.suppression_enabled ? 'true' : 'false'}
                  onChange={(e) => setConfig({ ...config, suppression_enabled: e.target.value === 'true' })}
                >
                  <option value="true">是</option>
                  <option value="false">否</option>
                </Select>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>配置说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-gray-600">
            <p><strong>自动解决超时:</strong> 告警在指定时间后自动标记为已解决</p>
            <p><strong>每个源最大告警数:</strong> 单个告警源允许的最大告警数量</p>
            <p><strong>数据保留天数:</strong> 告警历史数据的保留时间</p>
            <p><strong>通知冷却时间:</strong> 同一告警的最小通知间隔</p>
            <p><strong>智能分析:</strong> 启用AI驱动的告警智能分析</p>
            <p><strong>告警预测:</strong> 启用基于机器学习的告警预测</p>
            <p><strong>告警关联:</strong> 启用告警之间的关联分析</p>
            <p><strong>告警升级:</strong> 启用未处理告警的自动升级</p>
            <p><strong>告警抑制:</strong> 启用基于规则的告警抑制</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
