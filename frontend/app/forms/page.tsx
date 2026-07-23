'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface FormField {
  id: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'checkbox';
  options?: string[];
  value: any;
  condition?: (values: Record<string, any>) => boolean;
}

export default function FormsPage() {
  const [activeTab, setActiveTab] = useState('dynamic');
  const [dynamicFields, setDynamicFields] = useState<FormField[]>([
    { id: 'name', label: '名称', type: 'text', value: '' },
    { id: 'type', label: '类型', type: 'select', options: ['服务器', '数据库', '缓存'], value: '服务器' },
    { id: 'cpu', label: 'CPU核心数', type: 'number', value: 2 },
    { id: 'memory', label: '内存(GB)', type: 'number', value: 4 },
    { id: 'enableAutoScale', label: '启用自动伸缩', type: 'checkbox', value: false },
    { 
      id: 'minInstances', 
      label: '最小实例数', 
      type: 'number', 
      value: 1,
      condition: (values) => values.enableAutoScale 
    },
    { 
      id: 'maxInstances', 
      label: '最大实例数', 
      type: 'number', 
      value: 10,
      condition: (values) => values.enableAutoScale 
    },
  ]);

  const [wizardStep, setWizardStep] = useState(0);
  const [wizardData, setWizardData] = useState({
    basic: { name: '', description: '' },
    config: { cpu: 2, memory: 4 },
    advanced: { enableAutoScale: false, region: 'us-east' },
  });

  const [conditionalValues, setConditionalValues] = useState({
    resourceType: 'vm',
    os: 'linux',
    enableBackup: false,
    backupSchedule: 'daily',
    enableMonitoring: false,
    monitoringLevel: 'basic',
  });

  // 动态表单处理
  const handleDynamicFieldChange = (id: string, value: any) => {
    setDynamicFields(fields => 
      fields.map(field => 
        field.id === id ? { ...field, value } : field
      )
    );
  };

  const addDynamicField = () => {
    const newField: FormField = {
      id: `field-${Date.now()}`,
      label: '新字段',
      type: 'text',
      value: '',
    };
    setDynamicFields([...dynamicFields, newField]);
  };

  const removeDynamicField = (id: string) => {
    setDynamicFields(fields => fields.filter(field => field.id !== id));
  };

  // 表单向导处理
  const wizardSteps = [
    { id: 'basic', title: '基本信息', icon: '📝' },
    { id: 'config', title: '资源配置', icon: '⚙️' },
    { id: 'advanced', title: '高级设置', icon: '🔧' },
  ];

  const handleWizardNext = () => {
    if (wizardStep < wizardSteps.length - 1) {
      setWizardStep(wizardStep + 1);
    }
  };

  const handleWizardPrev = () => {
    if (wizardStep > 0) {
      setWizardStep(wizardStep - 1);
    }
  };

  const handleWizardSubmit = () => {
    alert('表单提交成功！');
    console.log(wizardData);
  };

  // 条件渲染表单处理
  const handleConditionalChange = (field: string, value: any) => {
    setConditionalValues(prev => ({ ...prev, [field]: value }));
  };

  const getVisibleDynamicFields = () => {
    const values = Object.fromEntries(
      dynamicFields.map(f => [f.id, f.value])
    );
    return dynamicFields.filter(field => 
      !field.condition || field.condition(values)
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">表单组件</h1>
        <div className="flex gap-2">
          <Button 
            variant={activeTab === 'dynamic' ? 'default' : 'outline'}
            onClick={() => setActiveTab('dynamic')}
          >
            动态表单
          </Button>
          <Button 
            variant={activeTab === 'wizard' ? 'default' : 'outline'}
            onClick={() => setActiveTab('wizard')}
          >
            表单向导
          </Button>
          <Button 
            variant={activeTab === 'conditional' ? 'default' : 'outline'}
            onClick={() => setActiveTab('conditional')}
          >
            条件渲染
          </Button>
        </div>
      </div>

      {/* 动态表单 */}
      {activeTab === 'dynamic' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>动态表单</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                {getVisibleDynamicFields().map((field) => (
                  <div key={field.id} className="flex items-start gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {field.label}
                      </label>
                      {field.type === 'text' && (
                        <Input
                          value={field.value}
                          onChange={(e) => handleDynamicFieldChange(field.id, e.target.value)}
                        />
                      )}
                      {field.type === 'number' && (
                        <Input
                          type="number"
                          value={field.value}
                          onChange={(e) => handleDynamicFieldChange(field.id, parseInt(e.target.value))}
                        />
                      )}
                      {field.type === 'select' && (
                        <Select
                          value={field.value}
                          onChange={(e) => handleDynamicFieldChange(field.id, e.target.value)}
                        >
                          {field.options?.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </Select>
                      )}
                      {field.type === 'checkbox' && (
                        <input
                          type="checkbox"
                          checked={field.value}
                          onChange={(e) => handleDynamicFieldChange(field.id, e.target.checked)}
                          className="w-4 h-4"
                        />
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => removeDynamicField(field.id)}
                    >
                      删除
                    </Button>
                  </div>
                ))}
              </div>
              <Button onClick={addDynamicField}>添加字段</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>表单数据</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-auto">
                {JSON.stringify(
                  Object.fromEntries(
                    dynamicFields.map(f => [f.id, f.value])
                  ),
                  null,
                  2
                )}
              </pre>
            </CardContent>
          </Card>
        </>
      )}

      {/* 表单向导 */}
      {activeTab === 'wizard' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>表单向导</CardTitle>
            </CardHeader>
            <CardContent>
              {/* 步骤指示器 */}
              <div className="flex items-center justify-between mb-8">
                {wizardSteps.map((step, index) => (
                  <div key={step.id} className="flex items-center">
                    <div
                      className={`flex items-center justify-center w-10 h-10 rounded-full ${
                        index <= wizardStep
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-600'
                      }`}
                    >
                      {step.icon}
                    </div>
                    <div className="ml-2">
                      <p className={`text-sm font-medium ${
                        index <= wizardStep ? 'text-blue-600' : 'text-gray-400'
                      }`}>
                        {step.title}
                      </p>
                    </div>
                    {index < wizardSteps.length - 1 && (
                      <div className="flex-1 mx-4 h-0.5 bg-gray-200" />
                    )}
                  </div>
                ))}
              </div>

              {/* 步骤内容 */}
              <div className="space-y-4">
                {wizardStep === 0 && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        名称
                      </label>
                      <Input
                        value={wizardData.basic.name}
                        onChange={(e) => setWizardData({
                          ...wizardData,
                          basic: { ...wizardData.basic, name: e.target.value }
                        })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        描述
                      </label>
                      <Input
                        value={wizardData.basic.description}
                        onChange={(e) => setWizardData({
                          ...wizardData,
                          basic: { ...wizardData.basic, description: e.target.value }
                        })}
                      />
                    </div>
                  </div>
                )}

                {wizardStep === 1 && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        CPU核心数
                      </label>
                      <Input
                        type="number"
                        value={wizardData.config.cpu}
                        onChange={(e) => setWizardData({
                          ...wizardData,
                          config: { ...wizardData.config, cpu: parseInt(e.target.value) }
                        })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        内存(GB)
                      </label>
                      <Input
                        type="number"
                        value={wizardData.config.memory}
                        onChange={(e) => setWizardData({
                          ...wizardData,
                          config: { ...wizardData.config, memory: parseInt(e.target.value) }
                        })}
                      />
                    </div>
                  </div>
                )}

                {wizardStep === 2 && (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={wizardData.advanced.enableAutoScale}
                        onChange={(e) => setWizardData({
                          ...wizardData,
                          advanced: { ...wizardData.advanced, enableAutoScale: e.target.checked }
                        })}
                        className="w-4 h-4"
                      />
                      <label className="text-sm font-medium text-gray-700">
                        启用自动伸缩
                      </label>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        区域
                      </label>
                      <Select
                        value={wizardData.advanced.region}
                        onChange={(e) => setWizardData({
                          ...wizardData,
                          advanced: { ...wizardData.advanced, region: e.target.value }
                        })}
                      >
                        <option value="us-east">us-east</option>
                        <option value="us-west">us-west</option>
                        <option value="eu-west">eu-west</option>
                        <option value="ap-southeast">ap-southeast</option>
                      </Select>
                    </div>
                  </div>
                )}
              </div>

              {/* 导航按钮 */}
              <div className="flex justify-between mt-8">
                <Button
                  variant="outline"
                  onClick={handleWizardPrev}
                  disabled={wizardStep === 0}
                >
                  上一步
                </Button>
                {wizardStep === wizardSteps.length - 1 ? (
                  <Button onClick={handleWizardSubmit}>提交</Button>
                ) : (
                  <Button onClick={handleWizardNext}>下一步</Button>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* 条件渲染 */}
      {activeTab === 'conditional' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>条件渲染表单</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  资源类型
                </label>
                <Select
                  value={conditionalValues.resourceType}
                  onChange={(e) => handleConditionalChange('resourceType', e.target.value)}
                >
                  <option value="vm">虚拟机</option>
                  <option value="container">容器</option>
                  <option value="serverless">无服务器</option>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  操作系统
                </label>
                <Select
                  value={conditionalValues.os}
                  onChange={(e) => handleConditionalChange('os', e.target.value)}
                >
                  <option value="linux">Linux</option>
                  <option value="windows">Windows</option>
                </Select>
              </div>

              {conditionalValues.resourceType === 'vm' && (
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-900 mb-2">虚拟机配置</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={conditionalValues.enableBackup}
                        onChange={(e) => handleConditionalChange('enableBackup', e.target.checked)}
                        className="w-4 h-4"
                      />
                      <label className="text-sm text-blue-800">启用备份</label>
                    </div>
                    {conditionalValues.enableBackup && (
                      <div>
                        <label className="block text-sm text-blue-800 mb-1">备份计划</label>
                        <Select
                          value={conditionalValues.backupSchedule}
                          onChange={(e) => handleConditionalChange('backupSchedule', e.target.value)}
                        >
                          <option value="daily">每日</option>
                          <option value="weekly">每周</option>
                          <option value="monthly">每月</option>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {conditionalValues.resourceType === 'container' && (
                <div className="p-4 bg-green-50 rounded-lg">
                  <h4 className="font-medium text-green-900 mb-2">容器配置</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={conditionalValues.enableMonitoring}
                        onChange={(e) => handleConditionalChange('enableMonitoring', e.target.checked)}
                        className="w-4 h-4"
                      />
                      <label className="text-sm text-green-800">启用监控</label>
                    </div>
                    {conditionalValues.enableMonitoring && (
                      <div>
                        <label className="block text-sm text-green-800 mb-1">监控级别</label>
                        <Select
                          value={conditionalValues.monitoringLevel}
                          onChange={(e) => handleConditionalChange('monitoringLevel', e.target.value)}
                        >
                          <option value="basic">基础</option>
                          <option value="advanced">高级</option>
                          <option value="enterprise">企业</option>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {conditionalValues.resourceType === 'serverless' && (
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h4 className="font-medium text-purple-900 mb-2">无服务器配置</h4>
                  <p className="text-sm text-purple-800">
                    无服务器资源自动管理基础设施，无需手动配置。
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>表单数据</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-auto">
                {JSON.stringify(conditionalValues, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </>
      )}

      {/* 功能说明 */}
      <Card>
        <CardHeader>
          <CardTitle>功能说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">动态表单</h4>
              <p className="text-sm text-gray-600">
                根据运行时条件动态添加或删除表单字段，支持灵活的数据收集。
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">表单向导</h4>
              <p className="text-sm text-gray-600">
                将复杂表单分解为多个步骤，逐步引导用户完成，提高用户体验。
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">条件渲染</h4>
              <p className="text-sm text-gray-600">
                根据用户选择动态显示或隐藏表单字段，简化表单界面。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
