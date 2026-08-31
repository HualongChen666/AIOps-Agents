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
  XCircle,
  AlertTriangle,
  Terminal,
  FolderOpen,
  Shield,
  Bug
} from 'lucide-react';

interface ScaffoldRequest {
  plugin_name: string;
  plugin_type: string;
  author: string;
  version: string;
  description: string;
  template: string;
}

interface ScaffoldResponse {
  success: boolean;
  plugin_id: string;
  plugin_path: string;
  message: string;
  created_files: string[];
}

interface ValidateRequest {
  plugin_code: string;
  plugin_config: Record<string, any>;
}

interface ValidateResponse {
  success: boolean;
  valid: boolean;
  errors: string[];
  warnings: string[];
  message: string;
}

interface TestRequest {
  plugin_code: string;
  test_config: Record<string, any>;
  test_data: Record<string, any>;
}

interface TestResponse {
  success: boolean;
  passed: boolean;
  test_results: Array<{ test: string; status: string; message: string }>;
  coverage: number | null;
  message: string;
}

interface BuildRequest {
  plugin_path: string;
  build_config: Record<string, any>;
}

interface BuildResponse {
  success: boolean;
  build_path: string;
  build_log: string;
  message: string;
}

interface PackageRequest {
  plugin_path: string;
  package_name?: string;
  version?: string;
  include_dependencies: boolean;
}

interface PackageResponse {
  success: boolean;
  package_path: string;
  package_name: string;
  package_size: number;
  message: string;
}

export default function PluginDevelopmentAdvancedPage() {
  const [activeTab, setActiveTab] = useState<'scaffold' | 'validate' | 'test' | 'build' | 'package'>('scaffold');
  const [scaffoldForm, setScaffoldForm] = useState<ScaffoldRequest>({
    plugin_name: '',
    plugin_type: 'collector',
    author: '',
    version: '1.0.0',
    description: '',
    template: 'default',
  });
  const [pluginCode, setPluginCode] = useState<string>('');
  const [pluginConfig, setPluginConfig] = useState<string>('');
  const [testConfig, setTestConfig] = useState<string>('');
  const [testData, setTestData] = useState<string>('');
  const [buildPath, setBuildPath] = useState<string>('');
  const [packagePath, setPackagePath] = useState<string>('');
  const [packageName, setPackageName] = useState<string>('');
  const [packageVersion, setPackageVersion] = useState<string>('');
  
  const [validateResult, setValidateResult] = useState<ValidateResponse | null>(null);
  const [testResult, setTestResult] = useState<TestResponse | null>(null);
  const [buildResult, setBuildResult] = useState<BuildResponse | null>(null);
  const [packageResult, setPackageResult] = useState<PackageResponse | null>(null);
  const [scaffoldResult, setScaffoldResult] = useState<ScaffoldResponse | null>(null);

  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const handleScaffold = async () => {
    if (!scaffoldForm.plugin_name || !scaffoldForm.plugin_type) {
      showError('请填写插件名称和类型');
      return;
    }

    try {
      const resp = await api.post('/api/v1/plugin/development/scaffolds', scaffoldForm);
      const result = resp.data as ScaffoldResponse;
      setScaffoldResult(result);
      if (result.success) {
        showSuccess(`插件脚手架创建成功: ${result.plugin_id}`);
      } else {
        showError(result.message);
      }
    } catch (error: any) {
      showError(`创建脚手架失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleValidate = async () => {
    if (!pluginCode) {
      showError('请输入插件代码');
      return;
    }

    try {
      const configObj = pluginConfig ? JSON.parse(pluginConfig) : {};
      const request: ValidateRequest = {
        plugin_code: pluginCode,
        plugin_config: configObj,
      };
      
      const resp = await api.post('/api/v1/plugin/development/validate', request);
      const result = resp.data as ValidateResponse;
      setValidateResult(result);
      if (result.success && result.valid) {
        showSuccess('插件验证通过');
      } else {
        showError('插件验证失败');
      }
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        showError('配置JSON格式错误');
      } else {
        showError(`验证失败: ${error.response?.data?.detail || error.message}`);
      }
    }
  };

  const handleTest = async () => {
    if (!pluginCode) {
      showError('请输入插件代码');
      return;
    }

    try {
      const testConfigObj = testConfig ? JSON.parse(testConfig) : {};
      const testDataObj = testData ? JSON.parse(testData) : {};
      
      const request: TestRequest = {
        plugin_code: pluginCode,
        test_config: testConfigObj,
        test_data: testDataObj,
      };
      
      const resp = await api.post('/api/v1/plugin/development/test', request);
      const result = resp.data as TestResponse;
      setTestResult(result);
      if (result.success && result.passed) {
        showSuccess('插件测试通过');
      } else {
        showError('插件测试失败');
      }
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        showError('测试配置或数据JSON格式错误');
      } else {
        showError(`测试失败: ${error.response?.data?.detail || error.message}`);
      }
    }
  };

  const handleBuild = async () => {
    if (!buildPath) {
      showError('请输入插件路径');
      return;
    }

    try {
      const request: BuildRequest = {
        plugin_path: buildPath,
        build_config: {},
      };
      
      const resp = await api.post('/api/v1/plugin/development/build', request);
      const result = resp.data as BuildResponse;
      setBuildResult(result);
      if (result.success) {
        showSuccess('插件构建成功');
      } else {
        showError('插件构建失败');
      }
    } catch (error: any) {
      showError(`构建失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handlePackage = async () => {
    if (!packagePath) {
      showError('请输入插件路径');
      return;
    }

    try {
      const request: PackageRequest = {
        plugin_path: packagePath,
        package_name: packageName || undefined,
        version: packageVersion || undefined,
        include_dependencies: true,
      };
      
      const resp = await api.post('/api/v1/plugin/development/package', request);
      const result = resp.data as PackageResponse;
      setPackageResult(result);
      if (result.success) {
        showSuccess(`插件打包成功: ${result.package_name}`);
      } else {
        showError('插件打包失败');
      }
    } catch (error: any) {
      showError(`打包失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const tabs = [
    { key: 'scaffold' as const, label: '创建脚手架', icon: Plus },
    { key: 'validate' as const, label: '代码验证', icon: Shield },
    { key: 'test' as const, label: '插件测试', icon: Bug },
    { key: 'build' as const, label: '构建插件', icon: Terminal },
    { key: 'package' as const, label: '打包发布', icon: Package },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Code className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">高级插件开发</h1>
            <p className="text-sm text-gray-500">完整的插件开发工作流：脚手架、验证、测试、构建、打包</p>
          </div>
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
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
                  activeTab === tab.key
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

      {activeTab === 'scaffold' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              创建插件脚手架
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">插件名称 *</label>
                  <Input
                    value={scaffoldForm.plugin_name}
                    onChange={(e) => setScaffoldForm({ ...scaffoldForm, plugin_name: e.target.value })}
                    placeholder="例如: MyCustomPlugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">插件类型 *</label>
                  <Select
                    value={scaffoldForm.plugin_type}
                    onChange={(e) => setScaffoldForm({ ...scaffoldForm, plugin_type: e.target.value })}
                  >
                    <option value="collector">数据采集器 (Collector)</option>
                    <option value="analyzer">数据分析器 (Analyzer)</option>
                    <option value="notifier">通知器 (Notifier)</option>
                    <option value="action">动作执行器 (Action)</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
                  <Input
                    value={scaffoldForm.author}
                    onChange={(e) => setScaffoldForm({ ...scaffoldForm, author: e.target.value })}
                    placeholder="插件作者名称"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
                  <Input
                    value={scaffoldForm.version}
                    onChange={(e) => setScaffoldForm({ ...scaffoldForm, version: e.target.value })}
                    placeholder="例如: 1.0.0"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                  <Textarea
                    value={scaffoldForm.description}
                    onChange={(e) => setScaffoldForm({ ...scaffoldForm, description: e.target.value })}
                    placeholder="插件功能描述"
                    rows={3}
                  />
                </div>
              </div>
              <Button onClick={handleScaffold} className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                创建脚手架
              </Button>

              {scaffoldResult && (
                <div className="mt-4 p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    {scaffoldResult.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <div className="font-medium">{scaffoldResult.message}</div>
                  </div>
                  {scaffoldResult.success && (
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-500">插件ID:</span> {scaffoldResult.plugin_id}</div>
                      <div><span className="text-gray-500">路径:</span> {scaffoldResult.plugin_path}</div>
                      <div>
                        <span className="text-gray-500">创建的文件:</span>
                        <ul className="ml-4 mt-1">
                          {scaffoldResult.created_files.map((file, idx) => (
                            <li key={idx}>{file}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'validate' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              代码验证
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">插件代码 *</label>
                <Textarea
                  value={pluginCode}
                  onChange={(e) => setPluginCode(e.target.value)}
                  placeholder="输入要验证的插件代码"
                  className="font-mono text-sm h-64"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">插件配置 (JSON格式，可选)</label>
                <Textarea
                  value={pluginConfig}
                  onChange={(e) => setPluginConfig(e.target.value)}
                  placeholder='{"plugin_name": "MyPlugin", "plugin_type": "collector"}'
                  className="font-mono text-sm h-32"
                />
              </div>
              <Button onClick={handleValidate}>
                <Shield className="h-4 w-4 mr-2" />
                验证代码
              </Button>

              {validateResult && (
                <div className="mt-4 p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    {validateResult.valid ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <div className="font-medium">{validateResult.message}</div>
                  </div>
                  
                  {validateResult.errors.length > 0 && (
                    <div className="mb-3">
                      <div className="text-sm font-medium text-red-700 mb-1">错误:</div>
                      <ul className="text-sm text-red-600 list-disc ml-4">
                        {validateResult.errors.map((error, idx) => (
                          <li key={idx}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {validateResult.warnings.length > 0 && (
                    <div>
                      <div className="text-sm font-medium text-yellow-700 mb-1">警告:</div>
                      <ul className="text-sm text-yellow-600 list-disc ml-4">
                        {validateResult.warnings.map((warning, idx) => (
                          <li key={idx}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'test' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bug className="h-5 w-5" />
              插件测试
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">插件代码 *</label>
                <Textarea
                  value={pluginCode}
                  onChange={(e) => setPluginCode(e.target.value)}
                  placeholder="输入要测试的插件代码"
                  className="font-mono text-sm h-48"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">测试配置 (JSON格式，可选)</label>
                  <Textarea
                    value={testConfig}
                    onChange={(e) => setTestConfig(e.target.value)}
                    placeholder='{"config_key": "config_value"}'
                    className="font-mono text-sm h-24"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">测试数据 (JSON格式，可选)</label>
                  <Textarea
                    value={testData}
                    onChange={(e) => setTestData(e.target.value)}
                    placeholder='{"test_key": "test_value"}'
                    className="font-mono text-sm h-24"
                  />
                </div>
              </div>
              <Button onClick={handleTest}>
                <Bug className="h-4 w-4 mr-2" />
                运行测试
              </Button>

              {testResult && (
                <div className="mt-4 p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    {testResult.passed ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <div className="font-medium">{testResult.message}</div>
                  </div>
                  
                  {testResult.coverage !== null && (
                    <div className="mb-3 text-sm">
                      <span className="text-gray-500">代码覆盖率:</span> {testResult.coverage.toFixed(1)}%
                    </div>
                  )}
                  
                  <div>
                    <div className="text-sm font-medium mb-2">测试结果:</div>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>测试</TableHead>
                          <TableHead>状态</TableHead>
                          <TableHead>消息</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {testResult.test_results.map((result, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono text-sm">{result.test}</TableCell>
                            <TableCell>
                              <Badge variant={result.status === 'passed' ? 'default' : 'destructive'}>
                                {result.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm">{result.message}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'build' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              构建插件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">插件路径 *</label>
                <div className="flex gap-2">
                  <Input
                    value={buildPath}
                    onChange={(e) => setBuildPath(e.target.value)}
                    placeholder="例如: plugins/MyCustomPlugin"
                  />
                  <Button variant="outline">
                    <FolderOpen className="h-4 w-4 mr-2" />
                    浏览
                  </Button>
                </div>
              </div>
              <Button onClick={handleBuild}>
                <Terminal className="h-4 w-4 mr-2" />
                构建插件
              </Button>

              {buildResult && (
                <div className="mt-4 p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    {buildResult.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <div className="font-medium">{buildResult.message}</div>
                  </div>
                  
                  {buildResult.success && (
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-500">构建路径:</span> {buildResult.build_path}</div>
                      <div>
                        <span className="text-gray-500">构建日志:</span>
                        <pre className="mt-1 p-2 bg-gray-50 rounded text-xs overflow-auto">
                          {buildResult.build_log}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'package' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              打包发布
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">插件路径 *</label>
                <div className="flex gap-2">
                  <Input
                    value={packagePath}
                    onChange={(e) => setPackagePath(e.target.value)}
                    placeholder="例如: plugins/MyCustomPlugin"
                  />
                  <Button variant="outline">
                    <FolderOpen className="h-4 w-4 mr-2" />
                    浏览
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">包名称 (可选)</label>
                  <Input
                    value={packageName}
                    onChange={(e) => setPackageName(e.target.value)}
                    placeholder="留空自动生成"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">版本 (可选)</label>
                  <Input
                    value={packageVersion}
                    onChange={(e) => setPackageVersion(e.target.value)}
                    placeholder="留空使用配置文件版本"
                  />
                </div>
              </div>
              <Button onClick={handlePackage}>
                <Package className="h-4 w-4 mr-2" />
                打包插件
              </Button>

              {packageResult && (
                <div className="mt-4 p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    {packageResult.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <div className="font-medium">{packageResult.message}</div>
                  </div>
                  
                  {packageResult.success && (
                    <div className="space-y-2 text-sm">
                      <div><span className="text-gray-500">包路径:</span> {packageResult.package_path}</div>
                      <div><span className="text-gray-500">包名称:</span> {packageResult.package_name}</div>
                      <div><span className="text-gray-500">包大小:</span> {(packageResult.package_size / 1024).toFixed(2)} KB</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 工作流说明 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            开发工作流
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="p-4 border rounded-lg text-center">
              <Plus className="h-8 w-8 mx-auto mb-2 text-[var(--accent-blue)]" />
              <div className="font-medium mb-1">1. 创建脚手架</div>
              <div className="text-sm text-gray-600">从模板生成基础代码</div>
            </div>
            <div className="p-4 border rounded-lg text-center">
              <Code className="h-8 w-8 mx-auto mb-2 text-[var(--accent-green)]" />
              <div className="font-medium mb-1">2. 编写代码</div>
              <div className="text-sm text-gray-600">实现插件功能</div>
            </div>
            <div className="p-4 border rounded-lg text-center">
              <Shield className="h-8 w-8 mx-auto mb-2 text-[var(--accent-yellow)]" />
              <div className="font-medium mb-1">3. 验证测试</div>
              <div className="text-sm text-gray-600">验证代码正确性</div>
            </div>
            <div className="p-4 border rounded-lg text-center">
              <Terminal className="h-8 w-8 mx-auto mb-2 text-[var(--accent-cyan)]" />
              <div className="font-medium mb-1">4. 构建</div>
              <div className="text-sm text-gray-600">编译构建插件</div>
            </div>
            <div className="p-4 border rounded-lg text-center">
              <Package className="h-8 w-8 mx-auto mb-2 text-[var(--accent-purple)]" />
              <div className="font-medium mb-1">5. 打包发布</div>
              <div className="text-sm text-gray-600">打包分发插件</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
