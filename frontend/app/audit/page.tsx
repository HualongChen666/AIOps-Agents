'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface AuditLog {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  details: string;
  ip: string;
  status: 'success' | 'failed';
}

interface ComplianceReport {
  id: string;
  name: string;
  type: 'GDPR' | 'SOC2' | 'ISO27001' | 'HIPAA';
  status: 'compliant' | 'non-compliant' | 'pending';
  lastCheck: string;
  score: number;
}

interface AccessControl {
  id: string;
  user: string;
  role: string;
  permissions: string[];
  lastAccess: string;
}

export default function AuditPage() {
  const [activeTab, setActiveTab] = useState<'logs' | 'reports' | 'access' | 'retention'>('logs');
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([
    {
      id: 'LOG-001',
      timestamp: new Date().toISOString(),
      user: 'admin',
      action: 'UPDATE',
      resource: 'alert-rule-001',
      details: 'Updated threshold from 80 to 85',
      ip: '192.168.1.100',
      status: 'success',
    },
    {
      id: 'LOG-002',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      user: 'user1',
      action: 'DELETE',
      resource: 'service-003',
      details: 'Deleted service configuration',
      ip: '192.168.1.101',
      status: 'success',
    },
    {
      id: 'LOG-003',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      user: 'admin',
      action: 'CREATE',
      resource: 'slo-001',
      details: 'Created new SLO for API availability',
      ip: '192.168.1.100',
      status: 'success',
    },
    {
      id: 'LOG-004',
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      user: 'user2',
      action: 'LOGIN',
      resource: 'system',
      details: 'Failed login attempt - invalid credentials',
      ip: '192.168.1.102',
      status: 'failed',
    },
  ]);

  const [complianceReports, setComplianceReports] = useState<ComplianceReport[]>([
    {
      id: 'COMP-001',
      name: 'GDPR Compliance',
      type: 'GDPR',
      status: 'compliant',
      lastCheck: new Date().toISOString(),
      score: 95,
    },
    {
      id: 'COMP-002',
      name: 'SOC2 Type II',
      type: 'SOC2',
      status: 'pending',
      lastCheck: new Date(Date.now() - 86400000).toISOString(),
      score: 88,
    },
    {
      id: 'COMP-003',
      name: 'ISO 27001',
      type: 'ISO27001',
      status: 'compliant',
      lastCheck: new Date(Date.now() - 172800000).toISOString(),
      score: 92,
    },
  ]);

  const [accessControls, setAccessControls] = useState<AccessControl[]>([
    {
      id: 'AC-001',
      user: 'admin',
      role: 'Administrator',
      permissions: ['read', 'write', 'delete', 'admin'],
      lastAccess: new Date().toISOString(),
    },
    {
      id: 'AC-002',
      user: 'user1',
      role: 'Operator',
      permissions: ['read', 'write'],
      lastAccess: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 'AC-003',
      user: 'user2',
      role: 'Viewer',
      permissions: ['read'],
      lastAccess: new Date(Date.now() - 86400000).toISOString(),
    },
  ]);

  const [retentionPolicy, setRetentionPolicy] = useState({
    auditLogs: '90d',
    metrics: '365d',
    alerts: '180d',
    reports: '730d',
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
      case 'compliant':
        return 'bg-green-100 text-green-800';
      case 'failed':
      case 'non-compliant':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'GDPR':
        return 'bg-blue-100 text-blue-800';
      case 'SOC2':
        return 'bg-purple-100 text-purple-800';
      case 'ISO27001':
        return 'bg-green-100 text-green-800';
      case 'HIPAA':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'logs' as const, label: '操作日志' },
    { key: 'reports' as const, label: '合规报告' },
    { key: 'access' as const, label: '访问控制' },
    { key: 'retention' as const, label: '数据保留' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">合规审计</h1>
        <Button>导出审计日志</Button>
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

      {/* 操作日志 */}
      {activeTab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle>操作日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-4">
              <div className="flex gap-4">
                <Input placeholder="搜索用户..." className="max-w-xs" />
                <Select>
                  <option value="">所有操作</option>
                  <option value="CREATE">创建</option>
                  <option value="UPDATE">更新</option>
                  <option value="DELETE">删除</option>
                  <option value="LOGIN">登录</option>
                </Select>
                <Select>
                  <option value="">所有状态</option>
                  <option value="success">成功</option>
                  <option value="failed">失败</option>
                </Select>
                <Button>搜索</Button>
              </div>
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
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-sm">{log.id}</TableCell>
                    <TableCell className="text-sm">{new Date(log.timestamp).toLocaleString()}</TableCell>
                    <TableCell className="font-medium">{log.user}</TableCell>
                    <TableCell>{log.action}</TableCell>
                    <TableCell className="font-mono text-sm">{log.resource}</TableCell>
                    <TableCell className="text-sm text-gray-600">{log.details}</TableCell>
                    <TableCell className="font-mono text-sm">{log.ip}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(log.status)}>
                        {log.status === 'success' ? '成功' : '失败'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 合规报告 */}
      {activeTab === 'reports' && (
        <Card>
          <CardHeader>
            <CardTitle>合规报告</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {complianceReports.map((report) => (
                <Card key={report.id}>
                  <CardHeader>
                    <CardTitle className="text-sm">{report.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Badge className={getTypeColor(report.type)}>{report.type}</Badge>
                        <Badge className={getStatusColor(report.status)}>
                          {report.status === 'compliant' ? '合规' : report.status === 'non-compliant' ? '不合规' : '待检查'}
                        </Badge>
                      </div>
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-500">合规分数</span>
                          <span className="font-medium">{report.score}%</span>
                        </div>
                        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${report.score >= 90 ? 'bg-green-500' : report.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${report.score}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        最后检查: {new Date(report.lastCheck).toLocaleDateString()}
                      </div>
                      <Button variant="outline" size="sm" className="w-full">
                        查看详情
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <div className="flex justify-end">
              <Button>生成新报告</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 访问控制 */}
      {activeTab === 'access' && (
        <Card>
          <CardHeader>
            <CardTitle>访问控制审计</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>权限</TableHead>
                  <TableHead>最后访问</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accessControls.map((ac) => (
                  <TableRow key={ac.id}>
                    <TableCell className="font-medium">{ac.user}</TableCell>
                    <TableCell>{ac.role}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {ac.permissions.map((perm) => (
                          <Badge key={perm} variant="outline" className="text-xs">
                            {perm}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(ac.lastAccess).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm">
                        编辑权限
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 数据保留策略 */}
      {activeTab === 'retention' && (
        <Card>
          <CardHeader>
            <CardTitle>数据保留策略</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">审计日志保留期</label>
                <Select
                  value={retentionPolicy.auditLogs}
                  onChange={(e) => setRetentionPolicy({ ...retentionPolicy, auditLogs: e.target.value })}
                >
                  <option value="30d">30天</option>
                  <option value="90d">90天</option>
                  <option value="180d">180天</option>
                  <option value="365d">1年</option>
                  <option value="730d">2年</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">指标数据保留期</label>
                <Select
                  value={retentionPolicy.metrics}
                  onChange={(e) => setRetentionPolicy({ ...retentionPolicy, metrics: e.target.value })}
                >
                  <option value="90d">90天</option>
                  <option value="180d">180天</option>
                  <option value="365d">1年</option>
                  <option value="730d">2年</option>
                  <option value="1825d">5年</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警数据保留期</label>
                <Select
                  value={retentionPolicy.alerts}
                  onChange={(e) => setRetentionPolicy({ ...retentionPolicy, alerts: e.target.value })}
                >
                  <option value="30d">30天</option>
                  <option value="90d">90天</option>
                  <option value="180d">180天</option>
                  <option value="365d">1年</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">报告数据保留期</label>
                <Select
                  value={retentionPolicy.reports}
                  onChange={(e) => setRetentionPolicy({ ...retentionPolicy, reports: e.target.value })}
                >
                  <option value="365d">1年</option>
                  <option value="730d">2年</option>
                  <option value="1825d">5年</option>
                  <option value="3650d">10年</option>
                </Select>
              </div>
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  ⚠️ 注意：缩短数据保留期将永久删除历史数据，此操作不可逆。
                </p>
              </div>
              <div className="flex justify-end">
                <Button>保存策略</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
