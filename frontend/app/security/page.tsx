'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface SecurityAlert {
  id: string;
  timestamp: string;
  type: 'threat' | 'vulnerability' | 'compliance' | 'incident';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  source: string;
  affectedAssets: number;
  status: 'open' | 'investigating' | 'resolved' | 'closed';
}

interface ThreatIntel {
  id: string;
  threatName: string;
  threatType: string;
  confidence: number;
  ioc: string;
  firstSeen: string;
  lastSeen: string;
}

interface Incident {
  id: string;
  name: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'resolved';
  assignedTo: string;
  created: string;
  updated: string;
}

export default function SecurityPage() {
  // 🔧 P1-4: State Management
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [activeTab, setActiveTab] = useState<'alerts' | 'threats' | 'incidents' | 'compliance'>('alerts');

  const [securityAlerts, setSecurityAlerts] = useState<SecurityAlert[]>([]);

  const [threatIntel, setThreatIntel] = useState<ThreatIntel[]>([]);

  const [incidents, setIncidents] = useState<Incident[]>([]);

  const [securityStats, setSecurityStats] = useState({
    threat_count: 0,
    vulnerability_count: 0,
    compliance_rate: 100,
    affected_assets: 0,
  });

  const loadSecurityData = async () => {
    setLoading(true);
    try {
      const [eventsRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/events'),
        api.get('/api/v1/security/stats'),
      ]);
      const events = eventsRes.data?.events || [];
      const stats = statsRes.data || {};

      const alerts: SecurityAlert[] = events.map((log: any, idx: number) => ({
        id: log.id || `SEV-${idx}`,
        timestamp: log.timestamp || new Date().toISOString(),
        type: log.type || 'incident',
        severity: log.severity || 'low',
        title: log.title || '安全事件',
        description: log.description || '',
        source: log.source || 'unknown',
        affectedAssets: log.affectedAssets || 1,
        status: log.status || 'open',
      }));

      const threats: ThreatIntel[] = events
        .filter((e: any) => e.type === 'threat' || e.severity === 'high')
        .map((e: any, idx: number) => ({
          id: e.id || `THR-${idx}`,
          threatName: e.title || '未知威胁',
          threatType: e.type || 'threat',
          confidence: e.severity === 'high' ? 85 : 60,
          ioc: e.source || 'unknown',
          firstSeen: e.timestamp || new Date().toISOString(),
          lastSeen: e.timestamp || new Date().toISOString(),
        }));

      const incidentItems: Incident[] = events
        .filter((e: any) => e.severity === 'critical' || e.severity === 'high' || e.status === 'open')
        .map((e: any, idx: number) => ({
          id: e.id || `INC-${idx}`,
          name: e.title || '安全事件',
          severity: e.severity || 'high',
          status: e.status === 'resolved' ? 'resolved' : 'open',
          assignedTo: e.source || 'unknown',
          created: e.timestamp || new Date().toISOString(),
          updated: e.timestamp || new Date().toISOString(),
        }));

      setSecurityAlerts(alerts);
      setThreatIntel(threats);
      setIncidents(incidentItems);
      setSecurityStats({
        threat_count: stats.threat_count ?? alerts.filter((a) => a.type === 'threat').length,
        vulnerability_count: stats.vulnerability_count ?? 0,
        compliance_rate: stats.compliance_rate ?? 100,
        affected_assets: stats.affected_assets ?? 0,
      });
      setLoading(false);
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      setSecurityAlerts((prev) => prev.filter((a) => a.id !== alertId));
      success("Alert resolved successfully");
    } catch (err) {
      showError("Failed to resolve alert");
    }
  };

  useEffect(() => {
    loadSecurityData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

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
      case 'in_progress':
        return 'bg-red-100 text-red-800';
      case 'investigating':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'closed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'threat':
        return 'bg-red-100 text-red-800';
      case 'vulnerability':
        return 'bg-orange-100 text-orange-800';
      case 'compliance':
        return 'bg-blue-100 text-blue-800';
      case 'incident':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'alerts' as const, label: '安全告警' },
    { key: 'threats' as const, label: '威胁情报' },
    { key: 'incidents' as const, label: '事件响应' },
    { key: 'compliance' as const, label: '合规检查' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">安全中心</h1>
        <Button onClick={loadSecurityData}>刷新数据</Button>
      </div>

      {/* 安全概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">威胁告警</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{securityStats.threat_count}</p>
            <p className="text-sm text-gray-500">活跃威胁</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">漏洞扫描</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{securityStats.vulnerability_count}</p>
            <p className="text-sm text-gray-500">高危漏洞</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">合规检查</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{securityStats.compliance_rate}%</p>
            <p className="text-sm text-gray-500">合规率</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">受影响资产</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{securityStats.affected_assets}</p>
            <p className="text-sm text-gray-500">需要关注</p>
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

      {/* 安全告警 */}
      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle>安全告警聚合</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 mb-4">
              <div className="flex gap-4">
                <Input placeholder="搜索告警..." className="max-w-xs" />
                <Select>
                  <option value="">所有类型</option>
                  <option value="threat">威胁</option>
                  <option value="vulnerability">漏洞</option>
                  <option value="compliance">合规</option>
                  <option value="incident">事件</option>
                </Select>
                <Select>
                  <option value="">所有严重性</option>
                  <option value="critical">严重</option>
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </Select>
              </div>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>严重性</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {securityAlerts.length > 0 ? securityAlerts.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell>{new Date(alert.timestamp).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(alert.type)}>{alert.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(alert.severity)}>{alert.severity}</Badge>
                    </TableCell>
                    <TableCell>{alert.title}</TableCell>
                    <TableCell>{alert.source}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(alert.status)}>{alert.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => handleResolveAlert(alert.id)}>
                        处理
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No security alerts found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 威胁情报 */}
      {activeTab === 'threats' && (
        <Card>
          <CardHeader>
            <CardTitle>威胁情报</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {threatIntel.length === 0 ? (
                <p className="text-center text-gray-500 py-8">暂无威胁情报</p>
              ) : (
                threatIntel.map((t) => (
                  <div key={t.id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{t.threatName}</span>
                      <Badge className={getSeverityColor('high')}>{t.threatType}</Badge>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">IOC: {t.ioc} · 置信度: {t.confidence}%</p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 事件响应 */}
      {activeTab === 'incidents' && (
        <Card>
          <CardHeader>
            <CardTitle>事件响应</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {incidents.length === 0 ? (
                <p className="text-center text-gray-500 py-8">暂无安全事件</p>
              ) : (
                incidents.map((inc) => (
                  <div key={inc.id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{inc.name}</span>
                      <Badge className={getStatusColor(inc.status)}>{inc.status}</Badge>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">严重度: {inc.severity} · 指派: {inc.assignedTo}</p>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 合规检查 */}
      {activeTab === 'compliance' && (
        <Card>
          <CardHeader>
            <CardTitle>合规检查</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {securityAlerts.filter((a) => a.type === 'compliance').length === 0 ? (
                <p className="text-center text-gray-500 py-8">暂无合规违规事件</p>
              ) : (
                securityAlerts
                  .filter((a) => a.type === 'compliance')
                  .map((a) => (
                    <div key={a.id} className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{a.title}</span>
                        <Badge className={getSeverityColor(a.severity)}>{a.severity}</Badge>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{a.description}</p>
                    </div>
                  ))
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
