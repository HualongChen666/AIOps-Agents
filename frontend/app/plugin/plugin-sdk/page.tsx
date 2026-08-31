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
  Book,
  Code,
  Download,
  FileText,
  Settings,
  Play,
  Plus,
  Zap,
  Layers,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Terminal,
  FolderOpen,
  Shield,
  Package,
  GitBranch,
  Globe,
  HelpCircle,
  Lightbulb
} from 'lucide-react';

interface SDKStatus {
  sdk_version: string;
  available: boolean;
  last_updated?: string;
  features?: string[];
  requirements?: string[];
}

interface SDKTemplate {
  name: string;
  description: string;
  category: string;
  methods: string[];
}

interface SDKDocumentation {
  version: string;
  sections: Array<{
    title: string;
    content: string;
    code_examples?: Array<{
      language: string;
      code: string;
    }>;
  }>;
}

interface GeneratedPlugin {
  plugin_id: string;
  plugin_name: string;
  version: string;
  template_type: string;
}

export default function PluginSdkPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'templates' | 'docs' | 'examples' | 'generate'>('overview');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [pluginName, setPluginName] = useState<string>('');
  const [className, setClassName] = useState<string>('');
  const [version, setVersion] = useState<string>('1.0.0');
  const [author, setAuthor] = useState<string>('');
  const [customConfig, setCustomConfig] = useState<string>('');
  const [generatedCode, setGeneratedCode] = useState<string>('');
  const [generatedConfig, setGeneratedConfig] = useState<string>('');
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);

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

      const result = resp.data.data;
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

      const result = resp.data.data;
      setGeneratedConfig(JSON.stringify(result, null, 2));
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
    { key: 'overview' as const, label: 'SDK概览', icon: Book },
    { key: 'templates' as const, label: '模板库', icon: Layers },
    { key: 'docs' as const, label: 'API文档', icon: FileText },
    { key: 'examples' as const, label: '代码示例', icon: Code },
    { key: 'generate' as const, label: '生成插件', icon: Plus },
  ];

  const templateDescriptions: Record<string, string> = {
    collector: '数据采集插件模板，用于从各种数据源收集指标、日志和事件数据',
    analyzer: '数据分析插件模板，用于处理和分析采集的数据，生成洞察和告警',
    notifier: '通知插件模板，用于发送告警通知到各种渠道（邮件、Slack、钉钉等）',
    transformer: '数据转换插件模板，用于转换和标准化数据格式',
    aggregator: '数据聚合插件模板，用于聚合和汇总多个数据源的数据',
  };

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
          description="无法加载插件SDK数据，请稍后重试"
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
          <Book className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">插件SDK</h1>
            <p className="text-sm text-gray-500">插件开发工具包和文档</p>
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

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2 flex-wrap">
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

      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* SDK状态 */}
          {sdkStatus && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
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

                {sdkStatus.features && sdkStatus.features.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm font-medium mb-2">SDK特性</div>
                    <div className="flex flex-wrap gap-2">
                      {sdkStatus.features.map((feature, idx) => (
                        <Badge key={idx} variant="outline">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {sdkStatus.requirements && sdkStatus.requirements.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm font-medium mb-2">系统要求</div>
                    <ul className="text-sm text-gray-600 list-disc ml-4">
                      {sdkStatus.requirements.map((req, idx) => (
                        <li key={idx}>{req}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 快速开始 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                快速开始
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-4 border rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-[var(--accent-blue)] text-white rounded-full font-bold">
                    1
                  </div>
                  <div>
                    <div className="font-medium">选择模板</div>
                    <div className="text-sm text-gray-600">从模板库中选择适合的插件类型模板</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-4 border rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-[var(--accent-blue)] text-white rounded-full font-bold">
                    2
                  </div>
                  <div>
                    <div className="font-medium">配置插件</div>
                    <div className="text-sm text-gray-600">填写插件名称、版本、作者等基本信息</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-4 border rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-[var(--accent-blue)] text-white rounded-full font-bold">
                    3
                  </div>
                  <div>
                    <div className="font-medium">生成代码</div>
                    <div className="text-sm text-gray-600">使用SDK生成插件代码和配置文件</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-4 border rounded-lg">
                  <div className="flex items-center justify-center w-8 h-8 bg-[var(--accent-blue)] text-white rounded-full font-bold">
                    4
                  </div>
                  <div>
                    <div className="font-medium">测试发布</div>
                    <div className="text-sm text-gray-600">测试插件功能并发布到插件市场</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
                      {templateDescriptions[template] || '通用插件模板'}
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

      {activeTab === 'docs' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              API文档
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-3">核心API</h3>
                <div className="space-y-3">
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">GET /api/plugin-sdk/status</div>
                    <div className="text-sm text-gray-600">获取SDK状态信息</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">GET /api/plugin-sdk/templates</div>
                    <div className="text-sm text-gray-600">获取可用的插件模板列表</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">POST /api/plugin-sdk/generate</div>
                    <div className="text-sm text-gray-600">生成插件包</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">GET /api/plugin-sdk/generate/code</div>
                    <div className="text-sm text-gray-600">生成插件代码</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">GET /api/plugin-sdk/generate/config</div>
                    <div className="text-sm text-gray-600">生成插件配置</div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-3">插件接口</h3>
                <div className="space-y-3">
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">initialize(config: Dict) -> bool</div>
                    <div className="text-sm text-gray-600">初始化插件，传入配置参数</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">cleanup() -> bool</div>
                    <div className="text-sm text-gray-600">清理插件资源</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">collect() -> Dict</div>
                    <div className="text-sm text-gray-600">采集数据（采集器插件）</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">analyze(data: Dict) -> Dict</div>
                    <div className="text-sm text-gray-600">分析数据（分析器插件）</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium mb-2">notify(alert: Dict) -> bool</div>
                    <div className="text-sm text-gray-600">发送通知（通知器插件）</div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'examples' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              代码示例
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium mb-3">基础插件示例</h3>
                <div className="p-4 bg-gray-900 rounded-lg">
                  <pre className="text-sm text-gray-100 overflow-x-auto">
                    {`# -*- coding: utf-8 -*-
"""
My Custom Plugin
示例插件
"""

from typing import Dict, Any
from loguru import logger

class MyCustomPlugin:
    """自定义插件示例"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plugin_name = "MyCustomPlugin"
        logger.info(f"Initialized {self.plugin_name}")
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self.config.update(config)
            logger.info(f"{self.plugin_name} initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理资源"""
        try:
            logger.info(f"{self.plugin_name} cleanup")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")
            return False`}
                  </pre>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-medium mb-3">配置文件示例</h3>
                <div className="p-4 bg-gray-900 rounded-lg">
                  <pre className="text-sm text-gray-100 overflow-x-auto">
                    {`{
  "plugin_id": "my-custom-plugin",
  "plugin_name": "My Custom Plugin",
  "plugin_type": "collector",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "My custom plugin description",
  "enabled": true,
  "config": {
    "interval": 60,
    "timeout": 30
  }
}`}
                  </pre>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'generate' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              生成插件
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
              <div className="flex gap-2">
                <Button onClick={handleGeneratePlugin} className="flex-1">
                  <Package className="h-4 w-4 mr-2" />
                  生成插件包
                </Button>
                <Button onClick={handleGenerateCode} variant="outline">
                  <Code className="h-4 w-4 mr-2" />
                  生成代码
                </Button>
                <Button onClick={handleGenerateConfig} variant="outline">
                  <Settings className="h-4 w-4 mr-2" />
                  生成配置
                </Button>
              </div>

              {generatedCode && (
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">生成的代码</label>
                    <Button onClick={handleDownloadCode} size="sm" variant="outline">
                      <Download className="h-4 w-4 mr-1" />
                      下载
                    </Button>
                  </div>
                  <Textarea
                    value={generatedCode}
                    readOnly
                    className="font-mono text-sm h-96"
                  />
                </div>
              )}

              {generatedConfig && (
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">生成的配置</label>
                    <Button onClick={handleDownloadConfig} size="sm" variant="outline">
                      <Download className="h-4 w-4 mr-1" />
                      下载
                    </Button>
                  </div>
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

      {/* 帮助提示 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            开发提示
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <HelpCircle className="h-4 w-4 text-[var(--accent-blue)]" />
                <div className="font-medium">命名规范</div>
              </div>
              <div className="text-sm text-gray-600">
                插件名称使用小写字母和连字符，类名使用驼峰命名法并添加Plugin后缀
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-4 w-4 text-[var(--accent-green)]" />
                <div className="font-medium">错误处理</div>
              </div>
              <div className="text-sm text-gray-600">
                所有方法都应该包含try-except错误处理，并记录日志
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Terminal className="h-4 w-4 text-[var(--accent-yellow)]" />
                <div className="font-medium">日志记录</div>
              </div>
              <div className="text-sm text-gray-600">
                使用loguru记录重要操作和错误信息，便于调试
              </div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <GitBranch className="h-4 w-4 text-[var(--accent-purple)]" />
                <div className="font-medium">版本管理</div>
              </div>
              <div className="text-sm text-gray-600">
                遵循语义化版本规范，及时更新版本号
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
