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

interface ComplianceStandard {
  id: string;
  name: string;
  type: 'iso27001' | 'pci_dss' | 'gdpr' | 'hipaa' | 'soc2' | 'nist';
  version: string;
  description: string;
  enabled: boolean;
}

interface ComplianceCheck {
  id: string;
  standardId: string;
  standardName: string;
  control: string;
  description: string;
  status: 'compliant' | 'non_compliant' | 'pending' | 'not_applicable';
  severity: 'critical' | 'high' | 'medium' | 'low';
  lastChecked: string;
  nextCheck: string;
  findings: string[];
}

interface ComplianceReport {
  id: string;
  standardId: string;
  standardName: string;
  generatedAt: string;
  overallScore: number;
  compliantControls: number;
  nonCompliantControls: number;
  pendingControls: number;
}

export default function ComplianceCheckPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [standards, setStandards] = useState<ComplianceStandard[]>([]);
  const [checks, setChecks] = useState<ComplianceCheck[]>([]);
  const [reports, setReports] = useState<ComplianceReport[]>([]);
  const [activeTab, setActiveTab] = useState<'checks' | 'standards' | 'reports'>('checks');
  const [selectedStandard, setSelectedStandard] = useState('');

  const loadComplianceData = async () => {
    setLoading(true);
    try {
      const [standardsRes, checksRes, reportsRes] = await Promise.all([
        api.get('/api/v1/security/compliance-check/standards'),
        api.get('/api/v1/security/compliance-check/checks', { params: { standardId: selectedStandard } }),
        api.get('/api/v1/security/compliance-check/reports'),
      ]);

      const standardsData = standardsRes.data?.standards || [];
      const checksData = checksRes.data?.checks || [];
      const reportsData = reportsRes.data?.reports || [];

      setStandards(standardsData);
      setChecks(checksData);
      setReports(reportsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleRunCheck = async (standardId: string) => {
    try {
      await api.post(`/api/v1/security/compliance-check/standards/${standardId}/run`);
      success('合规检查已启动');
      loadComplianceData();
    } catch (err) {
      showError('启动检查失败');
    }
  };

  const handleGenerateReport = async (standardId: string) => {
    try {
      await api.post(`/api/v1/security/compliance-check/standards/${standardId}/report`);
      success('报告生成中');
      loadComplianceData();
    } catch (err) {
      showError('报告生成失败');
    }
  };

  const handleToggleStandard = async (standardId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/compliance-check/standards/${standardId}`, { enabled });
      success('标准状态更新成功');
      loadComplianceData();
    } catch (err) {
      showError('状态更新失败');
    }
  };

  useEffect(() => {
    loadComplianceData();
  }, [selectedStandard]);

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
      case 'compliant':
        return 'bg-green-100 text-green-800';
      case 'non_compliant':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'not_applicable':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'checks' as const, label: '合规检查' },
    { key: 'standards' as const, label: '合规标准' },
    { key: 'reports' as const, label: '合规报告' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">合规检查</h1>
        <div className="flex gap-2">
          <Button onClick={loadComplianceData}>刷新数据</Button>
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

      {/* 合规检查 */}
      {activeTab === 'checks' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>筛选条件</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Select
                  value={selectedStandard}
                  onChange={(e) => setSelectedStandard(e.target.value)}
                >
                  <option value="">所有标准</option>
                  {standards.map((std) => (
                    <option key={std.id} value={std.id}>{std.name}</option>
                  ))}
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>合规检查结果</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>标准</TableHead>
                    <TableHead>控制</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>严重性</TableHead>
                    <TableHead>最后检查</TableHead>
                    <TableHead>下次检查</TableHead>
                    <TableHead>发现</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {checks.length > 0 ? checks.map((check) => (
                    <TableRow key={check.id}>
                      <TableCell>{check.standardName}</TableCell>
                      <TableCell className="font-medium">{check.control}</TableCell>
                      <TableCell className="text-sm max-w-xs truncate">{check.description}</TableCell>
                      <TableCell>
                        <Badge className={getStatusColor(check.status)}>{check.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getSeverityColor(check.severity)}>{check.severity}</Badge>
                      </TableCell>
                      <TableCell>{new Date(check.lastChecked).toLocaleString()}</TableCell>
                      <TableCell>{new Date(check.nextCheck).toLocaleString()}</TableCell>
                      <TableCell>{check.findings.length}</TableCell>
                    </TableRow>
                  )) : (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-gray-500">
                        No compliance checks found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {/* 合规标准 */}
      {activeTab === 'standards' && (
        <Card>
          <CardHeader>
            <CardTitle>合规标准</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {standards.length > 0 ? standards.map((standard) => (
                  <TableRow key={standard.id}>
                    <TableCell className="font-medium">{standard.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{standard.type.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{standard.version}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{standard.description}</TableCell>
                    <TableCell>
                      <Badge className={standard.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {standard.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRunCheck(standard.id)}
                          disabled={!standard.enabled}
                        >
                          运行检查
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleGenerateReport(standard.id)}
                          disabled={!standard.enabled}
                        >
                          生成报告
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleStandard(standard.id, !standard.enabled)}
                        >
                          {standard.enabled ? '禁用' : '启用'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-gray-500">
                      No compliance standards found
                    </TableCell>
                  </TableRow>
                )}
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>标准</TableHead>
                  <TableHead>生成时间</TableHead>
                  <TableHead>总体评分</TableHead>
                  <TableHead>合规控制</TableHead>
                  <TableHead>不合规控制</TableHead>
                  <TableHead>待定控制</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.length > 0 ? reports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell className="font-medium">{report.standardName}</TableCell>
                    <TableCell>{new Date(report.generatedAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={report.overallScore >= 80 ? 'bg-green-100 text-green-800' : report.overallScore >= 60 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}>
                        {report.overallScore}%
                      </Badge>
                    </TableCell>
                    <TableCell className="text-green-600">{report.compliantControls}</TableCell>
                    <TableCell className="text-red-600">{report.nonCompliantControls}</TableCell>
                    <TableCell className="text-yellow-600">{report.pendingControls}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm">
                        查看
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No compliance reports found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
