'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface AlertRule {
  id: string;
  name: string;
  metric: string;
  threshold: number;
  operator: '>' | '<' | '=' | '>=' | '<=';
  enabled: boolean;
}

interface HealStrategy {
  id: string;
  name: string;
  alertType: string;
  action: string;
  autoExecute: boolean;
}

interface ScalingPolicy {
  id: string;
  name: string;
  metric: string;
  minReplicas: number;
  maxReplicas: number;
  targetCPU: number;
  targetMemory: number;
  enabled: boolean;
}

interface User {
  id: string;
  username: string;
  name: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  disabled: boolean;
  status: 'active' | 'inactive';
  lastLogin: string;
}

interface AuditLog {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  details: string;
  ip: string;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'alerts' | 'heal' | 'scaling' | 'users' | 'audit' | 'integration'>('general');
  const [alertRules, setAlertRules] = useState<AlertRule[]>([
    { id: 'AR-001', name: 'CPU告警', metric: 'cpu_usage', threshold: 80, operator: '>', enabled: true },
    { id: 'AR-002', name: '内存告警', metric: 'memory_usage', threshold: 85, operator: '>', enabled: true },
    { id: 'AR-003', name: '磁盘告警', metric: 'disk_usage', threshold: 90, operator: '>', enabled: true },
  ]);

  const [healStrategies, setHealStrategies] = useState<HealStrategy[]>([
    {
      id: 'HS-001',
      name: '服务重启策略',
      alertType: 'service_down',
      action: 'restart_service',
      autoExecute: false,
    },
    {
      id: 'HS-002',
      name: '扩容策略',
      alertType: 'high_load',
      action: 'scale_up',
      autoExecute: false,
    },
  ]);

  const [scalingPolicies, setScalingPolicies] = useState<ScalingPolicy[]>([
    {
      id: 'SP-001',
      name: 'CPU自动扩缩容',
      metric: 'cpu_usage',
      minReplicas: 2,
      maxReplicas: 10,
      targetCPU: 70,
      targetMemory: 80,
      enabled: true,
    },
    {
      id: 'SP-002',
      name: '内存自动扩缩容',
      metric: 'memory_usage',
      minReplicas: 2,
      maxReplicas: 8,
      targetCPU: 75,
      targetMemory: 75,
      enabled: true,
    },
  ]);

  const [users, setUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const mapUser = (u: any): User => ({
    id: String(u.id),
    username: String(u.username),
    name: u.full_name || u.username,
    email: u.email || '',
    role: u.role === 'admin' ? 'admin' : u.role === 'operator' ? 'operator' : 'viewer',
    disabled: !!u.disabled,
    status: u.disabled ? 'inactive' : 'active',
    lastLogin: u.last_login_at || u.created_at || new Date().toISOString(),
  });

  const mapAuditLog = (l: any): AuditLog => ({
    id: String(l.id),
    timestamp: l.created_at || new Date().toISOString(),
    user: l.username || 'system',
    action: l.action || '',
    resource: `${l.resource_type || ''}${l.resource_id ? `/${l.resource_id}` : ''}`,
    details: l.details || '',
    ip: l.ip_address || '',
  });

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      try {
        const [usersRes, auditRes] = await Promise.all([
          api.get('/api/v1/users/'),
          api.get('/api/v1/users/audit-logs'),
        ]);
        if (!mounted) return;
        setUsers((usersRes.data || []).map(mapUser));
        setAuditLogs((auditRes.data || []).map(mapAuditLog));
      } catch {
        // api interceptor shows errors via toast
      }
    };
    loadData();
    return () => { mounted = false; };
  }, []);

  const handleToggleStatus = async (user: User) => {
    const newDisabled = !user.disabled;
    try {
      await api.put(`/api/v1/users/${user.username}`, { disabled: newDisabled });
      setUsers((prev) =>
        prev.map((u) =>
          u.id === user.id ? { ...u, disabled: newDisabled, status: newDisabled ? 'inactive' : 'active' } : u
        )
      );
    } catch {
      // api interceptor handles errors
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!window.confirm('确定要删除该用户吗？')) return;
    try {
      await api.delete(`/api/v1/users/${user.username}`);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch {
      // api interceptor handles errors
    }
  };

  const tabs = [
    { key: 'general' as const, label: '通用设置' },
    { key: 'alerts' as const, label: '告警规则' },
    { key: 'heal' as const, label: '修复策略' },
    { key: 'scaling' as const, label: '伸缩策略' },
    { key: 'users' as const, label: '用户管理' },
    { key: 'audit' as const, label: '审计日志' },
    { key: 'integration' as const, label: '集成配置' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">设置</h1>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
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

      {/* 通用设置 */}
      {activeTab === 'general' && (
        <Card>
          <CardHeader>
            <CardTitle>通用设置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">系统名称</label>
                <Input defaultValue="AIOps Agent" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">时区</label>
                <Select defaultValue="Asia/Shanghai">
                  <option value="Asia/Shanghai">Asia/Shanghai</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">语言</label>
                <Select defaultValue="zh-CN">
                  <option value="zh-CN">简体中文</option>
                  <option value="en-US">English</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">数据保留期</label>
                <Select defaultValue="30d">
                  <option value="7d">7天</option>
                  <option value="30d">30天</option>
                  <option value="90d">90天</option>
                  <option value="1y">1年</option>
                </Select>
              </div>
              <div className="flex justify-end">
                <Button>保存设置</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 告警规则 */}
      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle>告警规则</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {alertRules.map((rule) => (
                <div key={rule.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <span className="font-medium">{rule.name}</span>
                      <span className="text-sm text-gray-500">{rule.metric}</span>
                      <span className="text-sm text-gray-500">
                        {rule.operator} {rule.threshold}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm ${rule.enabled ? 'text-green-600' : 'text-gray-400'}`}>
                        {rule.enabled ? '启用' : '禁用'}
                      </span>
                      <Button variant="outline" size="sm">
                        编辑
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              <Button className="w-full">添加新规则</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 修复策略 */}
      {activeTab === 'heal' && (
        <Card>
          <CardHeader>
            <CardTitle>修复策略</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {healStrategies.map((strategy) => (
                <div key={strategy.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <span className="font-medium">{strategy.name}</span>
                      <span className="text-sm text-gray-500">{strategy.alertType}</span>
                      <span className="text-sm text-gray-500">{strategy.action}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-sm ${strategy.autoExecute ? 'text-green-600' : 'text-gray-400'}`}>
                        {strategy.autoExecute ? '自动执行' : '需审批'}
                      </span>
                      <Button variant="outline" size="sm">
                        编辑
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              <Button className="w-full">添加新策略</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 伸缩策略 */}
      {activeTab === 'scaling' && (
        <Card>
          <CardHeader>
            <CardTitle>伸缩策略配置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {scalingPolicies.map((policy) => (
                <div key={policy.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                      <span className="font-medium">{policy.name}</span>
                      <Badge className={policy.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {policy.enabled ? '启用' : '禁用'}
                      </Badge>
                    </div>
                    <Button variant="outline" size="sm">
                      编辑
                    </Button>
                  </div>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">指标:</span>
                      <span className="ml-2 font-medium">{policy.metric}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">最小副本:</span>
                      <span className="ml-2 font-medium">{policy.minReplicas}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">最大副本:</span>
                      <span className="ml-2 font-medium">{policy.maxReplicas}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">目标CPU:</span>
                      <span className="ml-2 font-medium">{policy.targetCPU}%</span>
                    </div>
                  </div>
                </div>
              ))}
              <Button className="w-full">添加伸缩策略</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 用户管理 */}
      {activeTab === 'users' && (
        <Card>
          <CardHeader>
            <CardTitle>用户权限管理</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button>添加用户</Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>邮箱</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>最后登录</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-mono text-sm">{user.id}</TableCell>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Badge className={user.role === 'admin' ? 'bg-purple-100 text-purple-800' : user.role === 'operator' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}>
                          {user.role === 'admin' ? '管理员' : user.role === 'operator' ? '运维' : '查看者'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={`cursor-pointer ${user.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}
                          onClick={() => handleToggleStatus(user)}
                        >
                          {user.status === 'active' ? '活跃' : '未激活'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{new Date(user.lastLogin).toLocaleString()}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">
                            编辑
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => handleDeleteUser(user)}>
                            删除
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 审计日志 */}
      {activeTab === 'audit' && (
        <Card>
          <CardHeader>
            <CardTitle>审计日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4">
                <Input placeholder="搜索日志..." className="max-w-xs" />
                <Select>
                  <option value="">所有操作</option>
                  <option value="CREATE">创建</option>
                  <option value="UPDATE">更新</option>
                  <option value="DELETE">删除</option>
                </Select>
                <Button>搜索</Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>时间</TableHead>
                    <TableHead>用户</TableHead>
                    <TableHead>操作</TableHead>
                    <TableHead>资源</TableHead>
                    <TableHead>详情</TableHead>
                    <TableHead>IP地址</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-sm">{log.id}</TableCell>
                      <TableCell className="text-sm">{new Date(log.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{log.user}</TableCell>
                      <TableCell>
                        <Badge className={log.action === 'CREATE' ? 'bg-green-100 text-green-800' : log.action === 'UPDATE' ? 'bg-blue-100 text-blue-800' : 'bg-red-100 text-red-800'}>
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell>{log.resource}</TableCell>
                      <TableCell className="text-sm">{log.details}</TableCell>
                      <TableCell className="font-mono text-sm">{log.ip}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 集成配置 */}
      {activeTab === 'integration' && (
        <Card>
          <CardHeader>
            <CardTitle>集成配置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API端点</label>
                <Input defaultValue="http://localhost:8000/api" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">WebSocket端点</label>
                <Input defaultValue="ws://localhost:8000/ws" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">通知渠道</label>
                <Select defaultValue="email">
                  <option value="email">邮件</option>
                  <option value="slack">Slack</option>
                  <option value="webhook">Webhook</option>
                  <option value="all">全部</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
                <Input placeholder="https://your-webhook-url.com" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">自定义配置</label>
                <Textarea rows={4} placeholder="输入自定义配置JSON..." />
              </div>
              <div className="flex justify-end">
                <Button>保存配置</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
