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

interface AuditReport {
  id: string;
  name: string;
  type: 'security' | 'compliance' | 'access' | 'performance';
  status: 'completed' | 'in_progress' | 'failed' | 'scheduled';
  createdAt: string;
  completedAt?: string;
  findings: number;
  criticalFindings: number;
  highFindings: number;
  mediumFindings: number;
  lowFindings: number;
  createdBy: string;
}

interface AuditSchedule {
  id: string;
  name: string;
  type: string;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  nextRun: string;
  lastRun: string;
  enabled: boolean;
}

interface AuditDashboard {
  totalReports: number;
  activeSchedules: number;
  totalFindings: number;
  criticalFindings: number;
  recentReports: AuditReport[];
}

export default function AuditCenterPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [schedules, setSchedules] = useState<AuditSchedule[]>([]);
  const [dashboard, setDashboard] = useState<AuditDashboard>({
    totalReports: 0,
    activeSchedules: 0,
    totalFindings: 0,
    criticalFindings: 0,
    recentReports: [],
  });
  const [activeTab, setActiveTab] = useState<'reports' | 'schedules' | 'dashboard'>('dashboard');
  const [showRunModal, setShowRunModal] = useState(false);
  const [newAudit, setNewAudit] = useState({
    name: '',
    type: 'security',
    target: '',
  });

  const loadAuditCenterData = async () => {
    setLoading(true);
    try {
      const [reportsRes, schedulesRes, dashboardRes] = await Promise.all([
        api.get('/api/v1/security/audit-center/reports'),
        api.get('/api/v1/security/audit-center/schedules'),
        api.get('/api/v1/security/audit-center/dashboard'),
      ]);

      const reportsData = reportsRes.data?.reports || [];
      const schedulesData = schedulesRes.data?.schedules || [];
      const dashboardData = dashboardRes.data || {};

      setReports(reportsData);
      setSchedules(schedulesData);
      setDashboard({
        totalReports: dashboardData.totalReports || reportsData.length,
        activeSchedules: dashboardData.activeSchedules || schedulesData.filter((s: AuditSchedule) => s.enabled).length,
        totalFindings: dashboardData.totalFindings || 0,
        criticalFindings: dashboardData.criticalFindings || 0,
        recentReports: dashboardData.recentReports || [],
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleRunAudit = async () => {
    try {
      await api.post('/api/v1/security/audit-center/run', newAudit);
      success('审计任务已启动');
      setShowRunModal(false);
      setNewAudit({ name: '', type: 'security', target: '' });
      loadAuditCenterData();
    } catch (err) {
      showError('启动审计失败');
    }
  };

  const handleToggleSchedule = async (scheduleId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/audit-center/schedules/${scheduleId}`, { enabled });
      success('调度状态更新成功');
      loadAuditCenterData();
    } catch (err) {
      showError('调度状态更新失败');
    }
  };

  const handleViewReport = async (reportId: string) => {
    try {
      const response = await api.get(`/api/v1/security/audit-center/reports/${reportId}/export`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit-report-${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      success('报告下载成功');
    } catch (err) {
      showError('报告下载失败');
    }
  };

  useEffect(() => {
    loadAuditCenterData();
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'scheduled':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'security':
        return 'bg-red-100 text-red-800';
      case 'compliance':
        return 'bg-blue-100 text-blue-800';
      case 'access':
        return 'bg-purple-100 text-purple-800';
      case 'performance':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'dashboard' as const, label: '仪表盘' },
    { key: 'reports' as const, label: '审计报告' },
    { key: 'schedules' as const, label: '调度任务' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">审计中心</h1>
        <div className="flex gap-2">
          <Button onClick={loadAuditCenterData}>刷新数据</Button>
          <Button onClick={() => setShowRunModal(true)}>运行审计</Button>
        </div>
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

      {/* 仪表盘 */}
      {activeTab === 'dashboard' && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">总报告数</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-blue-600">{dashboard.totalReports}</p>
                <p className="text-sm text-gray-500">审计报告</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">活跃调度</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-green-600">{dashboard.activeSchedules}</p>
                <p className="text-sm text-gray-500">定时任务</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">总发现</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-purple-600">{dashboard.totalFindings}</p>
                <p className="text-sm text-gray-500">审计发现</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">严重发现</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-red-600">{dashboard.criticalFindings}</p>
                <p className="text-sm text-gray-500">需要立即处理</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>最近报告</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>发现</TableHead>
                    <TableHead>严重</TableHead>
                    <TableHead>创建时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dashboard.recentReports.length > 0 ? dashboard.recentReports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell className="font-medium">{report.name}</TableCell>
                      <TableCell>
                        <Badge className={getTypeColor(report.type)}>{report.type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(report.status)}>{report.status}</Badge>
                      </TableCell>
                      <TableCell>{report.findings}</TableCell>
                      <TableCell className="text-red-600 font-bold">{report.criticalFindings}</TableCell>
                      <TableCell>{new Date(report.createdAt).toLocaleString()}</TableCell>
                    </TableRow>
                  )) : (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-gray-500">
                        No recent reports found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {/* 审计报告 */}
      {activeTab === 'reports' && (
        <Card>
          <CardHeader>
            <CardTitle>审计报告</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>总发现</TableHead>
                  <TableHead>严重</TableHead>
                  <TableHead>高</TableHead>
                  <TableHead>中</TableHead>
                  <TableHead>低</TableHead>
                  <TableHead>创建者</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.length > 0 ? reports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell className="font-medium">{report.name}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(report.type)}>{report.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(report.status)}>{report.status}</Badge>
                    </TableCell>
                    <TableCell>{report.findings}</TableCell>
                    <TableCell className="text-red-600 font-bold">{report.criticalFindings}</TableCell>
                    <TableCell className="text-orange-600">{report.highFindings}</TableCell>
                    <TableCell className="text-yellow-600">{report.mediumFindings}</TableCell>
                    <TableCell className="text-blue-600">{report.lowFindings}</TableCell>
                    <TableCell>{report.createdBy}</TableCell>
                    <TableCell>{new Date(report.createdAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewReport(report.id)}
                        disabled={report.status !== 'completed'}
                      >
                        查看
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center text-gray-500">
                      No audit reports found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 调度任务 */}
      {activeTab === 'schedules' && (
        <Card>
          <CardHeader>
            <CardTitle>调度任务</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>频率</TableHead>
                  <TableHead>下次运行</TableHead>
                  <TableHead>上次运行</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schedules.length > 0 ? schedules.map((schedule) => (
                  <TableRow key={schedule.id}>
                    <TableCell className="font-medium">{schedule.name}</TableCell>
                    <TableCell>{schedule.type}</TableCell>
                    <TableCell>{schedule.frequency}</TableCell>
                    <TableCell>{new Date(schedule.nextRun).toLocaleString()}</TableCell>
                    <TableCell>{new Date(schedule.lastRun).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={schedule.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {schedule.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleSchedule(schedule.id, !schedule.enabled)}
                      >
                        {schedule.enabled ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No scheduled tasks found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 运行审计模态框 */}
      {showRunModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>运行审计</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">审计名称</label>
                <Input
                  value={newAudit.name}
                  onChange={(e) => setNewAudit({ ...newAudit, name: e.target.value })}
                  placeholder="输入审计名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">审计类型</label>
                <Select
                  value={newAudit.type}
                  onChange={(e) => setNewAudit({ ...newAudit, type: e.target.value })}
                >
                  <option value="security">安全审计</option>
                  <option value="compliance">合规审计</option>
                  <option value="access">访问审计</option>
                  <option value="performance">性能审计</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">审计目标</label>
                <Input
                  value={newAudit.target}
                  onChange={(e) => setNewAudit({ ...newAudit, target: e.target.value })}
                  placeholder="输入审计目标"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowRunModal(false)}>取消</Button>
                <Button onClick={handleRunAudit}>运行</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
