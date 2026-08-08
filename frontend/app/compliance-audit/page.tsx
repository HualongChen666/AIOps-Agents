'use client'

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface AuditLog {
  id: string;
  timestamp: Date;
  user: string;
  action: string;
  resource: string;
  details: string;
  ip: string;
  status: 'success' | 'failure';
}

interface ComplianceReport {
  id: string;
  name: string;
  type: 'SOC2' | 'ISO27001' | 'GDPR' | 'HIPAA';
  status: 'compliant' | 'non-compliant' | 'pending';
  lastAudit: Date;
  nextAudit: Date;
  findings: number;
}

interface RetentionPolicy {
  resource: string;
  retentionPeriod: string;
  currentRetention: string;
  status: 'compliant' | 'non-compliant';
}

interface GuardStats {
  total: number;
  blocked_count: number;
  high_count: number;
  block_rate: number;
}

function mapGuardLogToAuditLog(raw: any, index: number): AuditLog {
  const result = String(raw?.result ?? '');
  const risk = String(raw?.risk_level ?? '');
  const isFailure = /fail|block|error/i.test(result) || risk === 'blocked' || raw?.status === 'failure';
  return {
    id: String(raw?.trace_id ?? `log-${index}`),
    timestamp: new Date(raw?.timestamp ?? Date.now()),
    user: String(raw?.who ?? 'unknown'),
    action: String(raw?.risk_level ?? raw?.result ?? 'UNKNOWN').toUpperCase(),
    resource: String(raw?.where ?? 'unknown'),
    details: String(raw?.what ?? ''),
    ip: String(raw?.where ?? 'unknown'),
    status: isFailure ? 'failure' : 'success',
  };
}

function buildComplianceReport(stats: GuardStats): ComplianceReport {
  const findings = (Number(stats?.high_count) || 0) + (Number(stats?.blocked_count) || 0);
  let status: 'compliant' | 'non-compliant' | 'pending' = 'compliant';
  if (findings > 0) {
    status = findings < 5 ? 'pending' : 'non-compliant';
  }
  return {
    id: 'CR-GUARD-001',
    name: '高危指令审计合规报告',
    type: 'SOC2',
    status,
    lastAudit: new Date(),
    nextAudit: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
    findings,
  };
}

export default function ComplianceAuditPage() {
  const [selectedTab, setSelectedTab] = useState('logs');
  const [searchQuery, setSearchQuery] = useState('');
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [complianceReports, setComplianceReports] = useState<ComplianceReport[]>([]);
  const [accessStats, setAccessStats] = useState<GuardStats>({
    total: 0,
    blocked_count: 0,
    high_count: 0,
    block_rate: 0,
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        const [logsRes, reportRes] = await Promise.all([
          api.get('/api/v1/audit', { params: { limit: 50 } }),
          api.get('/api/v1/audit/report', { params: { limit: 50 } }),
        ]);
        const rawLogs = logsRes.data ?? [];
        setAuditLogs(rawLogs.map((log: any, i: number) => mapGuardLogToAuditLog(log, i)));

        const report = reportRes.data ?? {};
        const total = Number(report.total) || 0;
        const riskDist = report.risk_distribution ?? {};
        const blockedCount = Number(riskDist.blocked) || 0;
        const highCount = Number(riskDist.high) || 0;
        const stats = {
          total,
          blocked_count: blockedCount,
          high_count: highCount,
          block_rate: total > 0 ? Math.round(((blockedCount + highCount) / total) * 100) : 0,
        };
        setAccessStats(stats);
        setComplianceReports([buildComplianceReport(stats)]);
      } catch (error) {
        // api.ts already shows toast on error
      }
    };
    loadData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
      case 'compliant':
        return 'bg-green-100 text-green-800';
      case 'failure':
      case 'non-compliant':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredLogs = auditLogs.filter(
    (log) =>
      log.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.resource.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const highRiskLogs = auditLogs.filter(
    (log) =>
      /high|blocked/i.test(log.action) ||
      log.status === 'failure'
  ).slice(0, 5);

  const [retentionPolicies] = useState<RetentionPolicy[]>([]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">合规审计</h1>
        <Button>生成合规报告</Button>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 border-b">
        <Button
          variant={selectedTab === 'logs' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('logs')}
        >
          操作日志
        </Button>
        <Button
          variant={selectedTab === 'access' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('access')}
        >
          访问审计
        </Button>
        <Button
          variant={selectedTab === 'data' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('data')}
        >
          数据审计
        </Button>
        <Button
          variant={selectedTab === 'reports' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('reports')}
        >
          合规报告
        </Button>
      </div>

      {/* 操作日志 */}
      {selectedTab === 'logs' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>操作日志</CardTitle>
              <div className="flex gap-2">
                <Input
                  placeholder="搜索日志..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64"
                />
                <Button variant="outline">导出</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {filteredLogs.map((log) => (
                <div key={log.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge className={getStatusColor(log.status)}>
                        {log.status === 'success' ? '成功' : '失败'}
                      </Badge>
                      <span className="font-medium">{log.action}</span>
                      <span className="text-gray-500">→</span>
                      <span className="text-sm">{log.resource}</span>
                    </div>
                    <span className="text-sm text-gray-500">{log.timestamp.toLocaleString()}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">用户: </span>
                      <span>{log.user}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">IP: </span>
                      <span>{log.ip}</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{log.details}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 访问审计 */}
      {selectedTab === 'access' && (
        <Card>
          <CardHeader>
            <CardTitle>访问审计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">最近访问统计</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">总访问次数</p>
                    <p className="text-2xl font-bold">{accessStats.total}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">失败/拦截访问</p>
                    <p className="text-2xl font-bold text-red-600">{accessStats.blocked_count}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">异常IP</p>
                    <p className="text-2xl font-bold text-yellow-600">{accessStats.high_count}</p>
                  </div>
                </div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">高风险访问</h4>
                <div className="space-y-2">
                  {highRiskLogs.length === 0 ? (
                    <p className="text-sm text-gray-500">暂无高风险访问记录</p>
                  ) : (
                    highRiskLogs.map((log) => (
                      <div
                        key={`risk-${log.id}`}
                        className="flex items-center justify-between p-2 bg-red-50 rounded"
                      >
                        <div>
                          <p className="text-sm font-medium">{log.action}</p>
                          <p className="text-xs text-gray-500">IP: {log.ip}</p>
                        </div>
                        <Badge className="bg-red-100 text-red-800">高风险</Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 数据审计 */}
      {selectedTab === 'data' && (
        <Card>
          <CardHeader>
            <CardTitle>数据保留策略</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {retentionPolicies.length === 0 ? (
                <p className="text-gray-500">暂无保留策略数据</p>
              ) : (
                retentionPolicies.map((policy, index) => (
                  <div key={index} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium">{policy.resource}</h4>
                      <Badge className={getStatusColor(policy.status)}>
                        {policy.status === 'compliant' ? '合规' : '不合规'}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">要求保留期: </span>
                        <span>{policy.retentionPeriod}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">当前保留期: </span>
                        <span className={policy.status === 'non-compliant' ? 'text-red-600' : ''}>
                          {policy.currentRetention}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="mt-4 pt-4 border-t">
              <Button variant="outline">配置保留策略</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 合规报告 */}
      {selectedTab === 'reports' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>合规报告</CardTitle>
              <Button variant="outline">生成新报告</Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {complianceReports.map((report) => (
                <div key={report.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="font-medium">{report.name}</h4>
                      <p className="text-sm text-gray-500">{report.type}</p>
                    </div>
                    <Badge className={getStatusColor(report.status)}>
                      {report.status === 'compliant' ? '合规' : report.status === 'non-compliant' ? '不合规' : '待审核'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">上次审计</p>
                      <p>{report.lastAudit.toLocaleDateString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">下次审计</p>
                      <p>{report.nextAudit.toLocaleDateString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">发现项</p>
                      <p className={report.findings > 0 ? 'text-yellow-600' : ''}>{report.findings}</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button variant="outline" size="sm">
                      导出PDF
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
