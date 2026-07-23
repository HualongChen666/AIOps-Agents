'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';

interface Component {
  id: string;
  name: string;
  type: 'chart' | 'metric' | 'table' | 'text';
  category: string;
  description: string;
  icon: string;
}

interface Dashboard {
  id: string;
  name: string;
  components: string[];
  createdAt: string;
  updatedAt: string;
}

interface AlertRule {
  id: string;
  name: string;
  condition: string;
  threshold: number;
  severity: 'low' | 'medium' | 'high';
  enabled: boolean;
}

export default function BuilderPage() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'alert' | 'report' | 'market'>('dashboard');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  
  const [components, setComponents] = useState<Component[]>([
    {
      id: 'CMP-001',
      name: '折线图',
      type: 'chart',
      category: '图表',
      description: '显示时间序列数据趋势',
      icon: '📈',
    },
    {
      id: 'CMP-002',
      name: '饼图',
      type: 'chart',
      category: '图表',
      description: '显示数据占比分布',
      icon: '🥧',
    },
    {
      id: 'CMP-003',
      name: '指标卡片',
      type: 'metric',
      category: '指标',
      description: '显示关键业务指标',
      icon: '📊',
    },
    {
      id: 'CMP-004',
      name: '数据表格',
      type: 'table',
      category: '表格',
      description: '显示结构化数据列表',
      icon: '📋',
    },
    {
      id: 'CMP-005',
      name: '文本组件',
      type: 'text',
      category: '文本',
      description: '显示自定义文本内容',
      icon: '📝',
    },
  ]);

  const [dashboards, setDashboards] = useState<Dashboard[]>([
    {
      id: 'DASH-001',
      name: '系统监控仪表盘',
      components: ['CMP-001', 'CMP-003', 'CMP-004'],
      createdAt: new Date(Date.now() - 86400000).toISOString(),
      updatedAt: new Date().toISOString(),
    },
    {
      id: 'DASH-002',
      name: '业务指标仪表盘',
      components: ['CMP-002', 'CMP-003'],
      createdAt: new Date(Date.now() - 172800000).toISOString(),
      updatedAt: new Date(Date.now() - 3600000).toISOString(),
    },
  ]);

  const [alertRules, setAlertRules] = useState<AlertRule[]>([
    {
      id: 'ALR-001',
      name: 'CPU使用率告警',
      condition: 'cpu_usage > threshold',
      threshold: 80,
      severity: 'high',
      enabled: true,
    },
    {
      id: 'ALR-002',
      name: '内存使用率告警',
      condition: 'memory_usage > threshold',
      threshold: 85,
      severity: 'medium',
      enabled: true,
    },
    {
      id: 'ALR-003',
      name: '磁盘空间告警',
      condition: 'disk_usage > threshold',
      threshold: 90,
      severity: 'high',
      enabled: false,
    },
  ]);

  const [newDashboard, setNewDashboard] = useState({
    name: '',
  });

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'chart':
        return 'bg-blue-100 text-blue-800';
      case 'metric':
        return 'bg-green-100 text-green-800';
      case 'table':
        return 'bg-purple-100 text-purple-800';
      case 'text':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateDashboard = () => {
    const dashboard: Dashboard = {
      id: `DASH-${String(dashboards.length + 1).padStart(3, '0')}`,
      name: newDashboard.name,
      components: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setDashboards([...dashboards, dashboard]);
    setShowCreateDialog(false);
    setNewDashboard({ name: '' });
  };

  const tabs = [
    { key: 'dashboard' as const, label: '仪表盘构建器' },
    { key: 'alert' as const, label: '告警规则构建器' },
    { key: 'report' as const, label: '报告生成器' },
    { key: 'market' as const, label: '组件市场' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">低代码构建器</h1>
        <Button onClick={() => setShowCreateDialog(true)}>新建项目</Button>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${
                  activeTab === tab.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 仪表盘构建器 */}
      {activeTab === 'dashboard' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>我的仪表盘</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead>组件数量</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead>更新时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dashboards.map((dashboard) => (
                    <TableRow key={dashboard.id}>
                      <TableCell className="font-mono text-sm">{dashboard.id}</TableCell>
                      <TableCell className="font-medium">{dashboard.name}</TableCell>
                      <TableCell>{dashboard.components.length}</TableCell>
                      <TableCell className="text-sm">{new Date(dashboard.createdAt).toLocaleString()}</TableCell>
                      <TableCell className="text-sm">{new Date(dashboard.updatedAt).toLocaleString()}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">
                            编辑
                          </Button>
                          <Button variant="outline" size="sm">
                            预览
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>可用组件</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {components.map((component) => (
                  <div
                    key={component.id}
                    className="p-4 border border-gray-200 rounded-lg hover:border-blue-500 cursor-pointer transition"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">{component.icon}</span>
                      <div>
                        <h3 className="font-medium">{component.name}</h3>
                        <Badge className={getTypeColor(component.type)}>{component.category}</Badge>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">{component.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 告警规则构建器 */}
      {activeTab === 'alert' && (
        <Card>
          <CardHeader>
            <CardTitle>告警规则构建器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex justify-end mb-4">
              <Button>创建规则</Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>规则名称</TableHead>
                  <TableHead>条件</TableHead>
                  <TableHead>阈值</TableHead>
                  <TableHead>严重级别</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alertRules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-mono text-sm">{rule.id}</TableCell>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell className="font-mono text-sm">{rule.condition}</TableCell>
                    <TableCell>{rule.threshold}%</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(rule.severity)}>
                        {rule.severity === 'high' ? '高' : rule.severity === 'medium' ? '中' : '低'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={rule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {rule.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">
                          编辑
                        </Button>
                        <Button variant="outline" size="sm">
                          {rule.enabled ? '禁用' : '启用'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 报告生成器 */}
      {activeTab === 'report' && (
        <Card>
          <CardHeader>
            <CardTitle>自定义报告生成器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-medium mb-3">报告模板</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition">
                    <div className="text-2xl mb-2">📊</div>
                    <h4 className="font-medium">系统健康报告</h4>
                    <p className="text-sm text-gray-600">包含系统整体健康度、资源使用情况</p>
                  </div>
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg cursor-pointer hover:bg-green-100 transition">
                    <div className="text-2xl mb-2">💰</div>
                    <h4 className="font-medium">成本分析报告</h4>
                    <p className="text-sm text-gray-600">包含成本趋势、优化建议</p>
                  </div>
                  <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg cursor-pointer hover:bg-purple-100 transition">
                    <div className="text-2xl mb-2">📈</div>
                    <h4 className="font-medium">性能分析报告</h4>
                    <p className="text-sm text-gray-600">包含性能指标、瓶颈分析</p>
                  </div>
                </div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-medium mb-3">自定义报告</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">报告名称</label>
                    <Input placeholder="输入报告名称" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">选择组件</label>
                    <div className="grid grid-cols-2 gap-2">
                      {components.map((component) => (
                        <label key={component.id} className="flex items-center gap-2 p-2 border border-gray-200 rounded cursor-pointer hover:bg-gray-50">
                          <input type="checkbox" className="rounded" />
                          <span>{component.icon} {component.name}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">生成周期</label>
                    <Select>
                      <option value="daily">每日</option>
                      <option value="weekly">每周</option>
                      <option value="monthly">每月</option>
                      <option value="manual">手动</option>
                    </Select>
                  </div>
                  <Button>创建报告</Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 组件市场 */}
      {activeTab === 'market' && (
        <Card>
          <CardHeader>
            <CardTitle>组件市场</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-4">
              <Input placeholder="搜索组件..." />
              <div className="flex gap-2">
                <Button variant="outline">全部</Button>
                <Button variant="outline">图表</Button>
                <Button variant="outline">指标</Button>
                <Button variant="outline">表格</Button>
                <Button variant="outline">文本</Button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {components.map((component) => (
                <Card key={component.id}>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span>{component.icon} {component.name}</span>
                      <Badge className={getTypeColor(component.type)}>{component.category}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 mb-3">{component.description}</p>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-500">v1.0.0</span>
                      <Button variant="outline" size="sm">
                        添加
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span>🗺️ 热力图</span>
                    <Badge className="bg-blue-100 text-blue-800">图表</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 mb-3">显示数据密度分布</p>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">v1.2.0</span>
                    <Button variant="outline" size="sm">
                      添加
                    </Button>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span>📊 桑基图</span>
                    <Badge className="bg-blue-100 text-blue-800">图表</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 mb-3">显示数据流向关系</p>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">v1.1.0</span>
                    <Button variant="outline" size="sm">
                      添加
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 创建项目弹窗 */}
      {showCreateDialog && (
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建新项目</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">项目类型</label>
                <Select>
                  <option value="dashboard">仪表盘</option>
                  <option value="alert">告警规则</option>
                  <option value="report">报告</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">项目名称</label>
                <Input
                  value={newDashboard.name}
                  onChange={(e) => setNewDashboard({ ...newDashboard, name: e.target.value })}
                  placeholder="例如：系统监控仪表盘"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">选择模板（可选）</label>
                <Select>
                  <option value="">空白模板</option>
                  <option value="system">系统监控模板</option>
                  <option value="business">业务指标模板</option>
                  <option value="performance">性能分析模板</option>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setShowCreateDialog(false)}>
                取消
              </Button>
              <Button onClick={handleCreateDashboard}>创建</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
