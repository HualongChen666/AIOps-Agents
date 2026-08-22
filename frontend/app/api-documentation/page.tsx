'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { BookOpen, RefreshCw, ExternalLink, Code, Zap, Shield, Database, Cloud } from 'lucide-react';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface ApiEndpoint {
  path: string;
  method: string;
  description: string;
  tags: string[];
}

export default function ApiDocumentationPage() {
  const [activeTab, setActiveTab] = useState<'swagger' | 'endpoints' | 'guides' | 'examples'>('swagger');
  const [showSwaggerModal, setShowSwaggerModal] = useState(false);

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load API documentation');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const apiEndpoints: ApiEndpoint[] = [
    { path: '/api/v1/alerts', method: 'GET', description: '获取告警列表', tags: ['告警管理'] },
    { path: '/api/v1/alerts', method: 'POST', description: '创建告警', tags: ['告警管理'] },
    { path: '/api/v1/metrics', method: 'GET', description: '获取系统指标', tags: ['监控'] },
    { path: '/api/v1/ai-advanced/predict/time-series', method: 'POST', description: '时序预测', tags: ['AI'] },
    { path: '/api/v1/root-cause/analyze', method: 'POST', description: '根因分析', tags: ['AI'] },
    { path: '/api/plugin-system/plugins', method: 'GET', description: '获取插件列表', tags: ['插件'] },
    { path: '/api/test-coverage/status', method: 'GET', description: '获取测试覆盖率', tags: ['测试'] },
    { path: '/api/documentation/documents', method: 'GET', description: '获取文档列表', tags: ['文档'] },
  ];

  const handleOpenSwagger = () => {
    window.open('/docs', '_blank');
  };

  const handleOpenReDoc = () => {
    window.open('/redoc', '_blank');
  };

  const handleOpenOpenAPI = () => {
    window.open('/openapi.json', '_blank');
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
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
          description="无法加载API文档，请稍后重试"
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">API文档</h1>
            <p className="text-sm text-gray-500">API接口文档和开发指南</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleOpenSwagger} variant="outline">
            <ExternalLink className="h-4 w-4 mr-2" />
            Swagger UI
          </Button>
          <Button onClick={handleOpenReDoc} variant="outline">
            <ExternalLink className="h-4 w-4 mr-2" />
            ReDoc
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">API端点</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">50+</p>
            <p className="text-sm text-gray-500 mt-1">可用API端点</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">API版本</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">v1.0</p>
            <p className="text-sm text-gray-500 mt-1">当前API版本</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">认证方式</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">JWT</p>
            <p className="text-sm text-gray-500 mt-1">Bearer Token</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">文档格式</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">OpenAPI</p>
            <p className="text-sm text-gray-500 mt-1">3.0规范</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'swagger' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('swagger')}
        >
          <BookOpen className="h-4 w-4 mr-2" />
          Swagger UI
        </Button>
        <Button
          variant={activeTab === 'endpoints' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('endpoints')}
        >
          <Code className="h-4 w-4 mr-2" />
          API端点
        </Button>
        <Button
          variant={activeTab === 'guides' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('guides')}
        >
          <Zap className="h-4 w-4 mr-2" />
          开发指南
        </Button>
        <Button
          variant={activeTab === 'examples' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('examples')}
        >
          <Database className="h-4 w-4 mr-2" />
          示例代码
        </Button>
      </div>

      {/* Swagger Tab */}
      {activeTab === 'swagger' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Swagger UI
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">交互式API文档</h3>
                <p className="text-gray-600 mb-4">
                  Swagger UI 提供交互式API文档，支持在线测试API端点。
                </p>
                <div className="flex gap-2">
                  <Button onClick={handleOpenSwagger}>
                    <ExternalLink className="h-4 w-4 mr-2" />
                    打开 Swagger UI
                  </Button>
                  <Button onClick={handleOpenReDoc} variant="outline">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    打开 ReDoc
                  </Button>
                  <Button onClick={handleOpenOpenAPI} variant="outline">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    OpenAPI JSON
                  </Button>
                </div>
              </div>
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">文档访问地址</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">Swagger UI:</span>
                    <code className="bg-gray-100 px-2 py-1 rounded">/docs</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">ReDoc:</span>
                    <code className="bg-gray-100 px-2 py-1 rounded">/redoc</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">OpenAPI Spec:</span>
                    <code className="bg-gray-100 px-2 py-1 rounded">/openapi.json</code>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Endpoints Tab */}
      {activeTab === 'endpoints' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              API端点列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {apiEndpoints.map((endpoint, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                        endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                        endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                        endpoint.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {endpoint.method}
                      </span>
                      <code className="text-sm">{endpoint.path}</code>
                    </div>
                    <div className="flex gap-1">
                      {endpoint.tags.map((tag) => (
                        <span key={tag} className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{endpoint.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Guides Tab */}
      {activeTab === 'guides' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              开发指南
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">快速开始</h3>
                <p className="text-gray-600 mb-4">
                  了解如何快速开始使用AIOps Agent API。
                </p>
                <Button variant="outline">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  查看快速开始指南
                </Button>
              </div>
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">认证说明</h3>
                <p className="text-gray-600 mb-4">
                  API使用JWT Bearer Token进行认证，需要在请求头中包含有效的token。
                </p>
                <Button variant="outline">
                  <Shield className="h-4 w-4 mr-2" />
                  查看认证文档
                </Button>
              </div>
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">错误处理</h3>
                <p className="text-gray-600 mb-4">
                  了解API错误响应格式和错误码说明。
                </p>
                <Button variant="outline">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  查看错误处理文档
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Examples Tab */}
      {activeTab === 'examples' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              示例代码
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">Python示例</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-x-auto">
{`import requests

# 配置API基础URL
BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key"

# 获取告警列表
response = requests.get(
    f"{BASE_URL}/api/v1/alerts",
    headers={"Authorization": f"Bearer {API_KEY}"}
)
alerts = response.json()
print(alerts)`}
                </pre>
              </div>
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">JavaScript示例</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-x-auto">
{`// 使用fetch API
const BASE_URL = 'http://localhost:8000';
const API_KEY = 'your-api-key';

// 获取告警列表
fetch(\`\${BASE_URL}/api/v1/alerts\`, {
  headers: {
    'Authorization': \`Bearer \${API_KEY}\`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));`}
                </pre>
              </div>
              <div className="border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-2">cURL示例</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-x-auto">
{`# 获取告警列表
curl -X GET http://localhost:8000/api/v1/alerts \\
  -H "Authorization: Bearer your-api-key"`}
                </pre>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}