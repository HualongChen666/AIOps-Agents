'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';

interface ChaosExperiment {
  id: string;
  name: string;
  type: 'cpu' | 'network' | 'disk' | 'service';
  target: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration: number;
  startTime: string;
  endTime?: string;
  impact: 'low' | 'medium' | 'high';
}

interface FaultTemplate {
  id: string;
  name: string;
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

export default function ChaosPage() {
  const [activeTab, setActiveTab] = useState<'experiments' | 'templates' | 'history' | 'results'>('experiments');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  
  const [experiments, setExperiments] = useState<ChaosExperiment[]>([
    {
      id: 'EXP-001',
      name: 'CPU过载测试',
      type: 'cpu',
      target: 'api-gateway',
      status: 'completed',
      duration: 300,
      startTime: new Date(Date.now() - 3600000).toISOString(),
      endTime: new Date(Date.now() - 3300000).toISOString(),
      impact: 'medium',
    },
    {
      id: 'EXP-002',
      name: '网络延迟注入',
      type: 'network',
      target: 'database',
      status: 'running',
      duration: 600,
      startTime: new Date(Date.now() - 120000).toISOString(),
      impact: 'high',
    },
    {
      id: 'EXP-003',
      name: '磁盘故障模拟',
      type: 'disk',
      target: 'storage-service',
      status: 'pending',
      duration: 900,
      startTime: new Date(Date.now() + 300000).toISOString(),
      impact: 'high',
    },
  ]);

  const [templates, setTemplates] = useState<FaultTemplate[]>([
    {
      id: 'TPL-001',
      name: 'CPU过载',
      type: 'cpu',
      description: '模拟CPU使用率达到100%',
      severity: 'high',
    },
    {
      id: 'TPL-002',
      name: '网络延迟',
      type: 'network',
      description: '增加网络延迟500ms',
      severity: 'medium',
    },
    {
      id: 'TPL-003',
      name: '磁盘故障',
      type: 'disk',
      description: '模拟磁盘I/O失败',
      severity: 'high',
    },
    {
      id: 'TPL-004',
      name: '服务重启',
      type: 'service',
      description: '强制重启目标服务',
      severity: 'medium',
    },
  ]);

  const [newExperiment, setNewExperiment] = useState({
    name: '',
    type: 'cpu' as 'cpu' | 'network' | 'disk' | 'service',
    target: '',
    duration: 300,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
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

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'cpu':
        return 'bg-purple-100 text-purple-800';
      case 'network':
        return 'bg-blue-100 text-blue-800';
      case 'disk':
        return 'bg-orange-100 text-orange-800';
      case 'service':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateExperiment = () => {
    const experiment: ChaosExperiment = {
      id: `EXP-${String(experiments.length + 1).padStart(3, '0')}`,
      name: newExperiment.name,
      type: newExperiment.type,
      target: newExperiment.target,
      status: 'pending',
      duration: newExperiment.duration,
      startTime: new Date(Date.now() + 60000).toISOString(),
      impact: 'medium',
    };
    setExperiments([...experiments, experiment]);
    setShowCreateDialog(false);
    setNewExperiment({ name: '', type: 'cpu', target: '', duration: 300 });
  };

  const tabs = [
    { key: 'experiments' as const, label: '实验管理' },
    { key: 'templates' as const, label: '故障模板' },
    { key: 'history' as const, label: '实验历史' },
    { key: 'results' as const, label: '结果分析' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">混沌工程</h1>
        <Button onClick={() => setShowCreateDialog(true)}>创建实验</Button>
      </div>

      {/* 实验概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">运行中实验</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">1</p>
            <p className="text-sm text-gray-500">当前执行</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">待执行实验</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">1</p>
            <p className="text-sm text-gray-500">等待开始</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已完成实验</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">1</p>
            <p className="text-sm text-gray-500">成功完成</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">故障模板</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">4</p>
            <p className="text-sm text-gray-500">可用模板</p>
          </CardContent>
        </Card>
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

      {/* 实验管理 */}
      {activeTab === 'experiments' && (
        <Card>
          <CardHeader>
            <CardTitle>实验管理</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>实验名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>目标</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>持续时间</TableHead>
                  <TableHead>影响</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {experiments.map((exp) => (
                  <TableRow key={exp.id}>
                    <TableCell className="font-mono text-sm">{exp.id}</TableCell>
                    <TableCell className="font-medium">{exp.name}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(exp.type)}>
                        {exp.type === 'cpu' ? 'CPU' : exp.type === 'network' ? '网络' : exp.type === 'disk' ? '磁盘' : '服务'}
                      </Badge>
                    </TableCell>
                    <TableCell>{exp.target}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(exp.status)}>
                        {exp.status === 'running' ? '运行中' : exp.status === 'completed' ? '已完成' : exp.status === 'failed' ? '失败' : '待执行'}
                      </Badge>
                    </TableCell>
                    <TableCell>{exp.duration}s</TableCell>
                    <TableCell>
                      <Badge className={getImpactColor(exp.impact)}>
                        {exp.impact === 'high' ? '高' : exp.impact === 'medium' ? '中' : '低'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{new Date(exp.startTime).toLocaleString()}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {exp.status === 'running' && (
                          <Button variant="outline" size="sm">
                            停止
                          </Button>
                        )}
                        {exp.status === 'pending' && (
                          <Button variant="outline" size="sm">
                            启动
                          </Button>
                        )}
                        <Button variant="outline" size="sm">
                          详情
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

      {/* 故障模板 */}
      {activeTab === 'templates' && (
        <Card>
          <CardHeader>
            <CardTitle>故障场景模板库</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {templates.map((template) => (
                <Card key={template.id}>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span>{template.name}</span>
                      <Badge className={getTypeColor(template.type)}>
                        {template.type}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                    <div className="flex items-center justify-between">
                      <Badge className={getImpactColor(template.severity)}>
                        {template.severity === 'high' ? '高风险' : template.severity === 'medium' ? '中风险' : '低风险'}
                      </Badge>
                      <Button variant="outline" size="sm">
                        使用模板
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 实验历史 */}
      {activeTab === 'history' && (
        <Card>
          <CardHeader>
            <CardTitle>实验历史</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>实验名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>结束时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {experiments.filter(exp => exp.status === 'completed' || exp.status === 'failed').map((exp) => (
                  <TableRow key={exp.id}>
                    <TableCell className="font-mono text-sm">{exp.id}</TableCell>
                    <TableCell className="font-medium">{exp.name}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(exp.type)}>
                        {exp.type === 'cpu' ? 'CPU' : exp.type === 'network' ? '网络' : exp.type === 'disk' ? '磁盘' : '服务'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(exp.status)}>
                        {exp.status === 'completed' ? '已完成' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{new Date(exp.startTime).toLocaleString()}</TableCell>
                    <TableCell className="text-sm">{exp.endTime ? new Date(exp.endTime).toLocaleString() : '-'}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm">
                        查看详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 结果分析 */}
      {activeTab === 'results' && (
        <Card>
          <CardHeader>
            <CardTitle>实验结果分析</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-medium mb-2">EXP-001: CPU过载测试</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">状态:</span>
                    <span className="ml-2 font-medium">已完成</span>
                  </div>
                  <div>
                    <span className="text-gray-500">持续时间:</span>
                    <span className="ml-2 font-medium">300s</span>
                  </div>
                  <div>
                    <span className="text-gray-500">故障影响:</span>
                    <span className="ml-2 font-medium">中等</span>
                  </div>
                  <div>
                    <span className="text-gray-500">恢复时间:</span>
                    <span className="ml-2 font-medium">45s</span>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-gray-50 rounded">
                  <p className="text-sm text-gray-600">
                    <strong>结论:</strong> 系统在CPU过载情况下表现良好，自动扩容机制正常工作，恢复时间在预期范围内。
                  </p>
                </div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-medium mb-2">EXP-002: 网络延迟注入</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">状态:</span>
                    <span className="ml-2 font-medium text-blue-600">运行中</span>
                  </div>
                  <div>
                    <span className="text-gray-500">持续时间:</span>
                    <span className="ml-2 font-medium">600s</span>
                  </div>
                  <div>
                    <span className="text-gray-500">故障影响:</span>
                    <span className="ml-2 font-medium">高</span>
                  </div>
                  <div>
                    <span className="text-gray-500">已运行:</span>
                    <span className="ml-2 font-medium">120s</span>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-blue-50 rounded">
                  <p className="text-sm text-blue-800">
                    <strong>实时监控:</strong> 网络延迟已注入，正在监控系统响应时间和错误率变化。
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 创建实验弹窗 */}
      {showCreateDialog && (
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建混沌实验</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">实验名称</label>
                <Input
                  value={newExperiment.name}
                  onChange={(e) => setNewExperiment({ ...newExperiment, name: e.target.value })}
                  placeholder="例如：CPU过载测试"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">故障类型</label>
                <Select
                  value={newExperiment.type}
                  onChange={(e) => setNewExperiment({ ...newExperiment, type: e.target.value as any })}
                >
                  <option value="cpu">CPU过载</option>
                  <option value="network">网络延迟</option>
                  <option value="disk">磁盘故障</option>
                  <option value="service">服务重启</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">目标服务</label>
                <Input
                  value={newExperiment.target}
                  onChange={(e) => setNewExperiment({ ...newExperiment, target: e.target.value })}
                  placeholder="例如：api-gateway"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">持续时间 (秒)</label>
                <Input
                  value={newExperiment.duration}
                  onChange={(e) => setNewExperiment({ ...newExperiment, duration: Number(e.target.value) })}
                  type="number"
                  min="60"
                  max="3600"
                />
              </div>
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  ⚠️ 警告：混沌实验会对生产环境造成实际影响，请确保已获得适当授权并有回滚计划。
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setShowCreateDialog(false)}>
                取消
              </Button>
              <Button onClick={handleCreateExperiment}>创建实验</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
