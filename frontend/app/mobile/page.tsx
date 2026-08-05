'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';

interface RawAlert {
  id: string;
  title?: string;
  desc?: string;
  level?: string;
  raw_time?: string;
  time?: string;
  value?: number;
  category?: string;
  [key: string]: any;
}

interface Alert {
  id: string;
  title: string;
  desc: string;
  level: string;
  time: string;
  value?: number;
}

interface RawApproval {
  id?: string;
  alert_id: string;
  proposal?: string;
  status?: string;
  risk_level?: string;
  submitted_at?: string;
  [key: string]: any;
}

interface Approval {
  id: string;
  alertId: string;
  proposal: string;
  status: string;
  riskLevel: string;
  submittedAt: string;
}

interface Snapshot {
  timestamp?: string;
  cpu?: { usage_percent?: number };
  memory?: { usage_percent?: number };
  disk?: any;
  network?: { recv_speed_mb?: number; sent_speed_mb?: number };
  summary?: {
    total_alerts?: number;
    heal_rate?: number | string;
    repairs?: { heal_rate?: number | string };
  };
}

export default function MobilePage() {
  const [isMobile, setIsMobile] = useState(false);
  const [viewportWidth, setViewportWidth] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [snapshot, setSnapshot] = useState<Snapshot>({});
  const [severityFilter, setSeverityFilter] = useState('all');

  useEffect(() => {
    const checkMobile = () => {
      const width = window.innerWidth;
      setViewportWidth(width);
      setIsMobile(width < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [alertsRes, approvalsRes, snapshotRes] = await Promise.all([
        api.get('/api/v1/alerts/?limit=20'),
        api.get('/api/v1/approvals/pending'),
        api.get('/api/v1/metrics/snapshot'),
      ]);

      const rawAlerts: RawAlert[] = alertsRes.data?.alerts || alertsRes.data || [];
      setAlerts(
        rawAlerts.map((a) => ({
          id: a.id || String(Math.random()).slice(2),
          title: a.title || '未命名告警',
          desc: a.desc || a.description || '',
          level: a.level || 'warning',
          time: a.raw_time || a.time || a.timestamp || '-',
          value: typeof a.value === 'number' ? a.value : undefined,
        }))
      );

      const rawApprovals: RawApproval[] = approvalsRes.data?.items || approvalsRes.data || [];
      setApprovals(
        rawApprovals.map((ap) => ({
          id: ap.id || ap.alert_id || String(Math.random()).slice(2),
          alertId: ap.alert_id || ap.id || '',
          proposal: ap.proposal || ap.rule_name || '修复方案',
          status: ap.status || 'pending',
          riskLevel: ap.risk_level || 'low',
          submittedAt: ap.submitted_at || '-',
        }))
      );

      setSnapshot(snapshotRes.data || {});
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalAlerts = alerts.length;
  const criticalAlerts = alerts.filter((a) => a.level === 'critical').length;
  const pendingApprovals = approvals.length;

  const cpu = snapshot.cpu?.usage_percent ?? 0;
  const memory = snapshot.memory?.usage_percent ?? 0;
  const diskItem = Array.isArray(snapshot.disk) ? snapshot.disk[0] : snapshot.disk;
  const disk = typeof diskItem?.usage_percent === 'number' ? diskItem.usage_percent : 0;
  const netIn = snapshot.network?.recv_speed_mb ?? 0;
  const netOut = snapshot.network?.sent_speed_mb ?? 0;
  const healRate = snapshot.summary?.heal_rate ?? snapshot.summary?.repairs?.heal_rate ?? 0;

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'normal':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
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

  const getMetricColor = (value: number) => {
    if (value >= 90) return 'text-red-600';
    if (value >= 70) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getHealthText = () => {
    if (cpu >= 90 || memory >= 90 || disk >= 95) return '严重';
    if (cpu >= 70 || memory >= 70 || disk >= 80) return '警告';
    return '健康';
  };

  const getHealthColor = () => {
    const text = getHealthText();
    if (text === '严重') return 'bg-red-100 text-red-800';
    if (text === '警告') return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const filteredAlerts =
    severityFilter === 'all'
      ? alerts
      : alerts.filter((a) => a.level === severityFilter);

  const parseRate = (value: number | string) => {
    if (typeof value === 'number') return value;
    const cleaned = String(value).replace('%', '').trim();
    const parsed = parseFloat(cleaned);
    return Number.isNaN(parsed) ? 0 : parsed;
  };

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">移动仪表盘</h1>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm ${isMobile ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
            {isMobile ? '移动视图' : '桌面视图'}
          </span>
          <span className="text-sm text-gray-500">{viewportWidth}px</span>
          <Button size="sm" onClick={loadData} disabled={loading}>
            {loading ? '刷新中' : '刷新'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* 核心概览 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">告警总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{loading ? '-' : totalAlerts}</p>
            <p className="text-sm text-gray-500 mt-1">实时告警</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">严重告警</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-600">{loading ? '-' : criticalAlerts}</p>
            <p className="text-sm text-gray-500 mt-1">需立即处理</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">待审批</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">{loading ? '-' : pendingApprovals}</p>
            <p className="text-sm text-gray-500 mt-1">修复方案</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">系统状态</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold inline-block px-2 py-1 rounded ${getHealthColor()}`}>
              {loading ? '-' : getHealthText()}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 指标快照 */}
      <Card>
        <CardHeader>
          <CardTitle>系统指标快照</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-gray-500">加载中...</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">CPU</p>
                <p className={`text-xl font-bold ${getMetricColor(cpu)}`}>{cpu.toFixed(1)}%</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">内存</p>
                <p className={`text-xl font-bold ${getMetricColor(memory)}`}>{memory.toFixed(1)}%</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">磁盘</p>
                <p className={`text-xl font-bold ${getMetricColor(disk)}`}>{disk.toFixed(1)}%</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">网络入</p>
                <p className="text-xl font-bold text-blue-600">{netIn.toFixed(1)} MB/s</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">网络出</p>
                <p className="text-xl font-bold text-blue-600">{netOut.toFixed(1)} MB/s</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">自愈成功率</p>
                <p className="text-xl font-bold text-green-600">{parseRate(healRate).toFixed(1)}%</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 最新告警 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>最新告警</CardTitle>
            <Select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="all">全部级别</option>
              <option value="critical">严重</option>
              <option value="warning">警告</option>
              <option value="normal">正常</option>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-gray-500">加载中...</div>
          ) : filteredAlerts.length === 0 ? (
            <div className="text-sm text-gray-500">暂无告警</div>
          ) : (
            <div className="space-y-3">
              {filteredAlerts.slice(0, 10).map((alert) => (
                <div key={alert.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm truncate pr-2">{alert.title}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${getLevelColor(alert.level)}`}>
                      {alert.level}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">{alert.desc}</p>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{alert.time}</span>
                    {typeof alert.value === 'number' && <span>值: {alert.value.toFixed(1)}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 待审批修复 */}
      <Card>
        <CardHeader>
          <CardTitle>待审批修复 ({pendingApprovals})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-gray-500">加载中...</div>
          ) : approvals.length === 0 ? (
            <div className="text-sm text-gray-500">暂无待审批修复方案</div>
          ) : (
            <div className="space-y-3">
              {approvals.map((ap) => (
                <div key={ap.id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{ap.alertId}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${getRiskColor(ap.riskLevel)}`}>
                      {ap.riskLevel}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">{ap.proposal}</p>
                  <div className="text-xs text-gray-500">提交于 {ap.submittedAt}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
