'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface SecurityAlert {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  type: string;
  source: string;
  timestamp: Date;
  status: 'open' | 'investigating' | 'resolved' | 'false-positive';
  affectedAssets: number;
}

interface ThreatIntel {
  id: string;
  threat: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  source: string;
  confidence: number;
  description: string;
  recommendedAction: string;
}

interface IncidentResponse {
  id: string;
  incident: string;
  phase: 'detection' | 'analysis' | 'containment' | 'eradication' | 'recovery';
  status: 'active' | 'completed';
  assignedTo: string;
  startTime: Date;
  progress: number;
}

interface AuditStats {
  total: number;
  level_counts: Record<string, number>;
  blocked_count: number;
  high_count: number;
  block_rate: number;
}

interface AuditLog {
  command: string;
  risk_level: string;
  executor: string;
  timestamp: string;
  host?: string;
  result?: string;
}

const riskSeverityMap: Record<string, 'critical' | 'high' | 'medium' | 'low'> = {
  blocked: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
  safe: 'low',
};

const riskStatusMap: Record<string, 'open' | 'investigating' | 'resolved' | 'false-positive'> = {
  blocked: 'open',
  high: 'investigating',
  medium: 'resolved',
  low: 'resolved',
  safe: 'resolved',
};

export default function SecurityEventsPage() {
  const [selectedTab, setSelectedTab] = useState('alerts');
  const [selectedAlert, setSelectedAlert] = useState<SecurityAlert | null>(null);
  const [securityAlerts, setSecurityAlerts] = useState<SecurityAlert[]>([]);
  const [threatIntel, setThreatIntel] = useState<ThreatIntel[]>([
    {
      id: 'TI-001',
      threat: 'CVE-2024-1234',
      severity: 'critical',
      source: 'CVE Database',
      confidence: 95,
      description: '远程代码执行漏洞',
      recommendedAction: '立即应用补丁',
    },
    {
      id: 'TI-002',
      threat: 'APT-29活动',
      severity: 'high',
      source: 'Threat Feed',
      confidence: 85,
      description: '国家级威胁组织活动',
      recommendedAction: '加强监控',
    },
  ]);
  const [incidentResponses, setIncidentResponses] = useState<IncidentResponse[]>([
    {
      id: 'IR-001',
      incident: 'SQL注入攻击响应',
      phase: 'containment',
      status: 'active',
      assignedTo: 'Security Team',
      startTime: new Date(Date.now() - 3600000),
      progress: 60,
    },
    {
      id: 'IR-002',
      incident: 'DDoS攻击响应',
      phase: 'recovery',
      status: 'active',
      assignedTo: 'Ops Team',
      startTime: new Date(Date.now() - 86400000),
      progress: 90,
    },
  ]);
  const [stats, setStats] = useState<AuditStats | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [auditRes, statsRes] = await Promise.all([
          api.get('/api/guard/audit', { params: { limit: 50 } }),
          api.get('/api/guard/stats'),
        ]);
        const logs: AuditLog[] = auditRes.data?.logs || [];
        const mappedAlerts: SecurityAlert[] = logs.map((log, index) => ({
          id: `SEC-${String(index + 1).padStart(3, '0')}`,
          title: log.command || '未知命令',
          severity: riskSeverityMap[log.risk_level] || 'low',
          type: `指令风险: ${log.risk_level || 'unknown'}`,
          source: log.executor || 'unknown',
          timestamp: log.timestamp ? new Date(log.timestamp) : new Date(),
          status: riskStatusMap[log.risk_level] || 'investigating',
          affectedAssets: 1,
        }));
        setSecurityAlerts(mappedAlerts);
        setStats(statsRes.data);
      } catch (error) {
        // errors already toasted by api interceptor
      }
    };
    loadData();
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-red-100 text-red-800';
      case 'investigating':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'false-positive':
        return 'bg-gray-100 text-gray-800';
      case 'active':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'detection':
        return 'bg-blue-100 text-blue-800';
      case 'analysis':
        return 'bg-purple-100 text-purple-800';
      case 'containment':
        return 'bg-orange-100 text-orange-800';
      case 'eradication':
        return 'bg-red-100 text-red-800';
      case 'recovery':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const activeCount = securityAlerts.filter(
    (a) => a.status === 'open' || a.status === 'investigating'
  ).length;
  const highCount = stats
    ? (stats.high_count ?? 0) + (stats.blocked_count ?? 0)
    : securityAlerts.filter((a) => a.severity === 'high' || a.severity === 'critical').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">安全事件管理</h1>
        <Button>生成合规报告</Button>
      </div>

      {/* 安全概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">威胁等级</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">高</p>
            <p className="text-xs text-gray-500">{highCount}个严重威胁</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">受影响资产</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{stats?.total ?? securityAlerts.length}</p>
            <p className="text-xs text-gray-500">需要立即关注</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃事件</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{activeCount}</p>
            <p className="text-xs text-gray-500">正在处理中</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">拦截率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-600">{stats ? `${stats.block_rate}%` : '-'}</p>
            <p className="text-xs text-gray-500">{stats?.blocked_count ?? '-'} 条被拦截</p>
          </CardContent>
        </Card>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 border-b">
        <Button
          variant={selectedTab === 'alerts' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('alerts')}
        >
          威胁告警
        </Button>
        <Button
          variant={selectedTab === 'intel' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('intel')}
        >
          威胁情报
        </Button>
        <Button
          variant={selectedTab === 'response' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('response')}
        >
          事件响应
        </Button>
        <Button
          variant={selectedTab === 'compliance' ? 'default' : 'outline'}
          onClick={() => setSelectedTab('compliance')}
        >
          合规报告
        </Button>
      </div>

      {/* 威胁告警 */}
      {selectedTab === 'alerts' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>安全告警聚合</CardTitle>
              <div className="flex gap-2">
                <select className="border border-gray-300 rounded px-3 py-1 text-sm">
                  <option>全部严重级别</option>
                  <option>严重</option>
                  <option>高</option>
                  <option>中</option>
                  <option>低</option>
                </select>
                <Button variant="outline">导出</Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {securityAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${selectedAlert?.id === alert.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  onClick={() => setSelectedAlert(alert)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge className={getSeverityColor(alert.severity)}>
                        {alert.severity === 'critical' ? '严重' : alert.severity === 'high' ? '高' : alert.severity === 'medium' ? '中' : '低'}
                      </Badge>
                      <span className="font-medium">{alert.title}</span>
                    </div>
                    <Badge className={getStatusColor(alert.status)}>
                      {alert.status === 'open' ? '待处理' : alert.status === 'investigating' ? '调查中' : alert.status === 'resolved' ? '已解决' : '误报'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">类型: </span>
                      <span>{alert.type}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">来源: </span>
                      <span>{alert.source}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">受影响资产: </span>
                      <span>{alert.affectedAssets}</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">{alert.timestamp.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 威胁情报 */}
      {selectedTab === 'intel' && (
        <Card>
          <CardHeader>
            <CardTitle>威胁情报集成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {threatIntel.map((intel) => (
                <div key={intel.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge className={getSeverityColor(intel.severity)}>
                        {intel.severity === 'critical' ? '严重' : intel.severity === 'high' ? '高' : intel.severity === 'medium' ? '中' : '低'}
                      </Badge>
                      <span className="font-medium">{intel.threat}</span>
                    </div>
                    <Badge variant="outline">置信度: {intel.confidence}%</Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{intel.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">来源: {intel.source}</span>
                    <span className="text-sm text-blue-600">{intel.recommendedAction}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 事件响应 */}
      {selectedTab === 'response' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>事件响应工作流</CardTitle>
              <Button>创建事件</Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {incidentResponses.map((incident) => (
                <div key={incident.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="font-medium">{incident.incident}</h4>
                      <p className="text-sm text-gray-500">负责人: {incident.assignedTo}</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge className={getStatusColor(incident.status)}>
                        {incident.status === 'active' ? '活跃' : '已完成'}
                      </Badge>
                      <Badge className={getPhaseColor(incident.phase)}>
                        {incident.phase === 'detection' ? '检测' : incident.phase === 'analysis' ? '分析' : incident.phase === 'containment' ? '遏制' : incident.phase === 'eradication' ? '清除' : '恢复'}
                      </Badge>
                    </div>
                  </div>
                  <div className="mb-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span>进度</span>
                      <span>{incident.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${incident.progress}%` }}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      查看详情
                    </Button>
                    <Button variant="outline" size="sm">
                      更新状态
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 合规报告 */}
      {selectedTab === 'compliance' && (
        <Card>
          <CardHeader>
            <CardTitle>安全合规报告</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">ISO 27001</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">状态</p>
                    <Badge className="bg-green-100 text-green-800">合规</Badge>
                  </div>
                  <div>
                    <p className="text-gray-500">上次审计</p>
                    <p>2024-01-15</p>
                  </div>
                  <div>
                    <p className="text-gray-500">发现项</p>
                    <p>0</p>
                  </div>
                </div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <h4 className="font-medium mb-2">SOC 2 Type II</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">状态</p>
                    <Badge className="bg-green-100 text-green-800">合规</Badge>
                  </div>
                  <div>
                    <p className="text-gray-500">上次审计</p>
                    <p>2024-02-01</p>
                  </div>
                  <div>
                    <p className="text-gray-500">发现项</p>
                    <p>2</p>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline">生成报告</Button>
                <Button variant="outline">导出PDF</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
