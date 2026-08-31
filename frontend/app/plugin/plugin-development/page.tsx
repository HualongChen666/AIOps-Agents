'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import {
  Code,
  Package,
  FileText,
  Settings,
  Download,
  Play,
  Plus,
  Zap,
  Layers,
  CheckCircle,
  XCircle
} from 'lucide-react';

interface SDKStatus {
  sdk_version: string;
  available: boolean;
  last_updated?: string;
}

interface PluginTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface GeneratedPlugin {
  plugin_id: string;
  plugin_name: string;
  version: string;
  template_type: string;
}

interface GeneratedCode {
  code: string;
  template_type: string;
  line_count: number;
}

interface PluginConfig {
  template_type: string;
  config: Record<string, any>;
}

export default function PluginDevelopmentPage() {
  const [activeTab, setActiveTab] = useState<'templates' | 'generate' | 'code' | 'config'>('templates');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [pluginName, setPluginName] = useState<string>('');
  const [className, setClassName] = useState<string>('');
  const [version, setVersion] = useState<string>('1.0.0');
  const [author, setAuthor] = useState<string>('');
  const [customConfig, setCustomConfig] = useState<string>('');
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string>('');
  const [generatedConfig, setGeneratedConfig] = useState<string>('');

  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 获取SDK状态
  const { data: sdkStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery<SDKStatus>({
    queryKey: ['plugin-sdk-status'],
    queryFn: async () => {
      const resp = await api.get('/api/plugin-sdk/status');
      return resp.data.data;
    },
    refetchInterval: 60000,
  });

  // 获取可用模板
  const { data: templatesData, isLoading: templatesLoading, refetch: refetchTemplates } = useQuery<{ templates: string[]; count: number }>({
    queryKey: ['plugin-sdk-templates'],
    queryFn: async () => {
      const resp = await api.get('/api/plugin-sdk/templates');
      return resp.data.data;
    },
    refetchInterval: 300000,
  });

  const { isLoading: pageLoading, error: pageError } = useLoadingState(statusLoading || templatesLoading);

  const handleGeneratePlugin = async () => {
    if (!selectedTemplate || !pluginName || !className) {
      showError('请填写所有必填字段');
      return;
    }

    try {
      const resp = await api.post('/api/plugin-sdk/generate', null, {
        params: {
          template_type: selectedTemplate,
          plugin_name: pluginName,
          class_name: className,
          version,
          author: author || 'Unknown',
        },
      });

      const result = resp.data.data as GeneratedPlugin;
      showSuccess(`插件生成成功: ${result.plugin_name} (${result.plugin_id})`);
      setGenerateDialogOpen(false);
      refetchStatus();
    } catch (error: any) {
      showError(`生成插件失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleGenerateCode = async () => {
    if (!selectedTemplate || !pluginName || !className) {
      showError('请填写所有必填字段');
      return;
    }

    try {
      const resp = await api.get('/api/plugin-sdk/generate/code', {
        params: {
          template_type: selectedTemplate,
          plugin_name: pluginName,
          class_name: className,
          version,
          author: author || 'Unknown',
        },
      });

      const result = resp.data.data as GeneratedCode;
      setGeneratedCode(result.code);
      showSuccess(`代码生成成功，共 ${result.line_count} 行`);
    } catch (error: any) {
      showError(`生成代码失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleGenerateConfig = async () => {
    if (!selectedTemplate) {
      showError('请选择模板类型');
      return;
    }

    try {
      const configObj = customConfig ? JSON.parse(customConfig) : undefined;
      const resp = await api.get('/api/plugin-sdk/generate/config', {
        params: {
          template_type: selectedTemplate,
        },
        data: configObj,
      });

      const result = resp.data.data as PluginConfig;
      setGeneratedConfig(JSON.stringify(result.config, null, 2));
      showSuccess('配置生成成功');
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        showError('自定义配置JSON格式错误');
      } else {
        showError(`生成配置失败: ${error.response?.data?.detail || error.message}`);
      }
    }
  };

  const handleDownloadCode = () => {
    if (!generatedCode) return;

    const blob = new Blob([generatedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${pluginName || 'plugin'}.py`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showSuccess('代码已下载');
  };

  const handleDownloadConfig = () => {
    if (!generatedConfig) return;

    const blob = new Blob([generatedConfig], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${pluginName || 'plugin'}_config.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showSuccess('配置已下载');
  };

  const tabs = [
    { key: 'templates' as const, label: '模板库', icon: Layers },
    { key: 'generate' as const, label: '生成插件', icon: Package },
    { key: 'code' as const, label: '生成代码', icon: Code },
    { key: 'config' as const, label: '生成配置', icon: Settings },
  ];

  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载插件开发工具，请稍后重试"
          action={<Button onClick={() => { refetchStatus(); refetchTemplates(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchStatus(); refetchTemplates(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Code className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">插件开发</h1>
            <p className="text-sm text-gray-500">使用SDK快速开发和生成插件</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {sdkStatus && (
            <Badge variant={sdkStatus.available ? 'default' : 'secondary'}>
              {sdkStatus.available ? (
                <>
                  <CheckCircle className="h-3 w-3 mr-1" />
                  SDK可用
                </>
              ) : (
                <>
                  <XCircle className="h-3 w-3 mr-1" />
                  SDK不可用
                </>
              )}
            </Badge>
          )}
          <Button onClick={() => { refetchStatus(); refetchTemplates(); }} variant="outline">
            刷新
          </Button>
        </div>
      </div>

      {/* SDK状态卡片 */}
      {sdkStatus && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              SDK状态
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">SDK版本</div>
                <div className="text-2xl font-bold text-[var(--accent-blue)]">
                  {sdkStatus.sdk_version || 'N/A'}
                </div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">状态</div>
                <Badge className={sdkStatus.available ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                  {sdkStatus.available ? '可用' : '不可用'}
                </Badge>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="text-sm text-gray-500 mb-1">最后更新</div>
                <div className="text-sm text-gray-700">
                  {sdkStatus.last_updated ? new Date(sdkStatus.last_updated).toLocaleString() : 'N/A'}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                    ? 'bg-[var(--accent-blue)] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {activeTab === 'templates' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              可用模板
            </CardTitle>
          </CardHeader>
          <CardContent>
            {templatesData && templatesData.templates && templatesData.templates.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {templatesData.templates.map((template) => (
                  <div
                    key={template}
                    className={`p-4 border rounded-lg cursor-pointer transition ${selectedTemplate === template
                        ? 'border-[var(--accent-blue)] bg-blue-50'
                        : 'hover:border-gray-300'
                      }`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium">{template}</div>
                      {selectedTemplate === template && (
                        <CheckCircle className="h-4 w-4 text-[var(--accent-blue)]" />
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      {template === 'collector' && '数据采集插件模板'}
                      {template === 'analyzer' && '数据分析插件模板'}
                      {template === 'notifier' && '通知插件模板'}
                      {template === 'transformer' && '数据转换插件模板'}
                      {template === 'aggregator' && '数据聚合插件模板'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="没有可用模板"
                description="插件SDK当前没有可用的模板"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'generate' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              生成插件包
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">模板类型 *</label>
                  <Select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                  >
                    <option value="">选择模板</option>
                    {templatesData?.templates?.map((template) => (
                      <option key={template} value={template}>
                        {template}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">插件名称 *</label>
                  <Input
                    value={pluginName}
                    onChange={(e) => setPluginName(e.target.value)}
                    placeholder="例如: MyCustomPlugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">类名 *</label>
                  <Input
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                    placeholder="例如: MyCustomPlugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
                  <Input
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="例如: 1.0.0"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
                  <Input
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="插件作者名称"
                  />
                </div>
              </div>
              <Button onClick={handleGeneratePlugin} className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                生成插件包
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'code' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              生成插件代码
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">模板类型 *</label>
                  <Select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                  >
                    <option value="">选择模板</option>
                    {templatesData?.templates?.map((template) => (
                      <option key={template} value={template}>
                        {template}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">插件名称 *</label>
                  <Input
                    value={pluginName}
                    onChange={(e) => setPluginName(e.target.value)}
                    placeholder="例如: MyCustomPlugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">类名 *</label>
                  <Input
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                    placeholder="例如: MyCustomPlugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
                  <Input
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="例如: 1.0.0"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleGenerateCode}>
                  <Play className="h-4 w-4 mr-2" />
                  生成代码
                </Button>
                {generatedCode && (
                  <Button onClick={handleDownloadCode} variant="outline">
                    <Download className="h-4 w-4 mr-2" />
                    下载代码
                  </Button>
                )}
              </div>
              {generatedCode && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">生成的代码</label>
                  <Textarea
                    value={generatedCode}
                    readOnly
                    className="font-mono text-sm h-96"
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'config' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              生成插件配置
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">模板类型 *</label>
                <Select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                >
                  <option value="">选择模板</option>
                  {templatesData?.templates?.map((template) => (
                    <option key={template} value={template}>
                      {template}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">自定义配置 (JSON格式，可选)</label>
                <Textarea
                  value={customConfig}
                  onChange={(e) => setCustomConfig(e.target.value)}
                  placeholder='{"key": "value"}'
                  className="font-mono text-sm h-32"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleGenerateConfig}>
                  <Play className="h-4 w-4 mr-2" />
                  生成配置
                </Button>
                {generatedConfig && (
                  <Button onClick={handleDownloadConfig} variant="outline">
                    <Download className="h-4 w-4 mr-2" />
                    下载配置
                  </Button>
                )}
              </div>
              {generatedConfig && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">生成的配置</label>
                  <Textarea
                    value={generatedConfig}
                    readOnly
                    className="font-mono text-sm h-64"
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
