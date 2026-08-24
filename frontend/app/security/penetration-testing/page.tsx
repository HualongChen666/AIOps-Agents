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

interface PentestProject {
  id: string;
  name: string;
  target: string;
  type: 'black_box' | 'gray_box' | 'white_box';
  status: 'planning' | 'in_progress' | 'completed' | 'on_hold';
  startDate: string;
  endDate: string;
  testers: string[];
  severity: 'critical' | 'high' | 'medium' | 'low';
  findings: number;
}

interface PentestFinding {
  id: string;
  projectId: string;
  title: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  cvssScore: number;
  description: string;
  proof: string;
  impact: string;
  remediation: string;
  status: 'open' | 'fixed' | 'accepted' | 'false_positive';
  discoveredAt: string;
}

interface PentestReport {
  id: string;
  projectId: string;
  title: string;
  generatedAt: string;
  format: 'pdf' | 'html' | 'json';
  size: number;
}

export default function PenetrationTestingPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [projects, setProjects] = useState<PentestProject[]>([]);
  const [findings, setFindings] = useState<PentestFinding[]>([]);
  const [reports, setReports] = useState<PentestReport[]>([]);
  const [activeTab, setActiveTab] = useState<'projects' | 'findings' | 'reports'>('projects');
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    target: '',
    type: 'black_box' as const,
    startDate: '',
    endDate: '',
  });
  const [selectedFinding, setSelectedFinding] = useState<PentestFinding | null>(null);

  const loadPentestData = async () => {
    setLoading(true);
    try {
      const [projectsRes, findingsRes, reportsRes] = await Promise.all([
        api.get('/api/v1/security/penetration-testing/projects'),
        api.get('/api/v1/security/penetration-testing/findings'),
        api.get('/api/v1/security/penetration-testing/reports'),
      ]);

      const projectsData = projectsRes.data?.projects || [];
      const findingsData = findingsRes.data?.findings || [];
      const reportsData = reportsRes.data?.reports || [];

      setProjects(projectsData);
      setFindings(findingsData);
      setReports(reportsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    try {
      await api.post('/api/v1/security/penetration-testing/projects', newProject);
      success('渗透测试项目创建成功');
      setShowNewProjectModal(false);
      setNewProject({ name: '', target: '', type: 'black_box', startDate: '', endDate: '' });
      loadPentestData();
    } catch (err) {
      showError('创建项目失败');
    }
  };

  const handleUpdateFinding = async (findingId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/penetration-testing/findings/${findingId}`, { status });
      success('发现状态更新成功');
      loadPentestData();
    } catch (err) {
      showError('状态更新失败');
    }
  };

  const handleGenerateReport = async (projectId: string) => {
    try {
      await api.post(`/api/v1/security/penetration-testing/projects/${projectId}/report`);
      success('报告生成中');
      loadPentestData();
    } catch (err) {
      showError('报告生成失败');
    }
  };

  const handleDownloadReport = async (reportId: string) => {
    try {
      const response = await api.get(`/api/v1/security/penetration-testing/reports/${reportId}/download`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pentest-report-${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      success('报告下载成功');
    } catch (err) {
      showError('报告下载失败');
    }
  };

  useEffect(() => {
    loadPentestData();
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
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'on_hold':
        return 'bg-yellow-100 text-yellow-800';
      case 'planning':
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
      case 'info':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getFindingStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-red-100 text-red-800';
      case 'fixed':
        return 'bg-green-100 text-green-800';
      case 'accepted':
        return 'bg-blue-100 text-blue-800';
      case 'false_positive':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'projects' as const, label: '测试项目' },
    { key: 'findings' as const, label: '发现结果' },
    { key: 'reports' as const, label: '测试报告' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">渗透测试</h1>
        <div className="flex gap-2">
          <Button onClick={loadPentestData}>刷新数据</Button>
          <Button onClick={() => setShowNewProjectModal(true)}>新建项目</Button>
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

      {/* 测试项目 */}
      {activeTab === 'projects' && (
        <Card>
          <CardHeader>
            <CardTitle>渗透测试项目</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>目标</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>开始日期</TableHead>
                  <TableHead>结束日期</TableHead>
                  <TableHead>测试人员</TableHead>
                  <TableHead>发现</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.length > 0 ? projects.map((project) => (
                  <TableRow key={project.id}>
                    <TableCell className="font-medium">{project.name}</TableCell>
                    <TableCell>{project.target}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{project.type.replace('_', ' ')}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(project.status)}>{project.status}</Badge>
                    </TableCell>
                    <TableCell>{new Date(project.startDate).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(project.endDate).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {project.testers.map((tester, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{tester}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>{project.findings}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleGenerateReport(project.id)}
                        disabled={project.status !== 'completed'}
                      >
                        生成报告
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-gray-500">
                      No penetration test projects found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 发现结果 */}
      {activeTab === 'findings' && (
        <Card>
          <CardHeader>
            <CardTitle>发现结果</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>标题</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>严重性</TableHead>
                  <TableHead>CVSS</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>发现时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {findings.length > 0 ? findings.map((finding) => (
                  <TableRow key={finding.id}>
                    <TableCell className="font-medium">{finding.title}</TableCell>
                    <TableCell>{finding.category}</TableCell>
                    <TableCell>
                      <Badge className={getSeverityColor(finding.severity)}>{finding.severity}</Badge>
                    </TableCell>
                    <TableCell>{finding.cvssScore.toFixed(1)}</TableCell>
                    <TableCell>
                      <Badge className={getFindingStatusColor(finding.status)}>{finding.status}</Badge>
                    </TableCell>
                    <TableCell>{new Date(finding.discoveredAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedFinding(finding)}
                        >
                          详情
                        </Button>
                        <Select
                          value={finding.status}
                          onChange={(e) => handleUpdateFinding(finding.id, e.target.value)}
                          className="w-32"
                        >
                          <option value="open">未修复</option>
                          <option value="fixed">已修复</option>
                          <option value="accepted">已接受</option>
                          <option value="false_positive">误报</option>
                        </Select>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No findings found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 测试报告 */}
      {activeTab === 'reports' && (
        <Card>
          <CardHeader>
            <CardTitle>测试报告</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>标题</TableHead>
                  <TableHead>项目ID</TableHead>
                  <TableHead>格式</TableHead>
                  <TableHead>大小</TableHead>
                  <TableHead>生成时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.length > 0 ? reports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell className="font-medium">{report.title}</TableCell>
                    <TableCell className="font-mono text-sm">{report.projectId}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{report.format.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{(report.size / 1024).toFixed(2)} KB</TableCell>
                    <TableCell>{new Date(report.generatedAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownloadReport(report.id)}
                      >
                        下载
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-gray-500">
                      No reports found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 新建项目模态框 */}
      {showNewProjectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>新建渗透测试项目</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">项目名称</label>
                <Input
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="输入项目名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">测试目标</label>
                <Input
                  value={newProject.target}
                  onChange={(e) => setNewProject({ ...newProject, target: e.target.value })}
                  placeholder="输入目标URL或IP地址"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">测试类型</label>
                <Select
                  value={newProject.type}
                  onChange={(e) => setNewProject({ ...newProject, type: e.target.value as any })}
                >
                  <option value="black_box">黑盒测试</option>
                  <option value="gray_box">灰盒测试</option>
                  <option value="white_box">白盒测试</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">开始日期</label>
                <Input
                  type="date"
                  value={newProject.startDate}
                  onChange={(e) => setNewProject({ ...newProject, startDate: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">结束日期</label>
                <Input
                  type="date"
                  value={newProject.endDate}
                  onChange={(e) => setNewProject({ ...newProject, endDate: e.target.value })}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowNewProjectModal(false)}>取消</Button>
                <Button onClick={handleCreateProject}>创建</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 发现详情模态框 */}
      {selectedFinding && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-3xl max-h-[80vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>发现详情</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">标题</label>
                  <p>{selectedFinding.title}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">分类</label>
                  <p>{selectedFinding.category}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">严重性</label>
                  <Badge className={getSeverityColor(selectedFinding.severity)}>{selectedFinding.severity}</Badge>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">CVSS评分</label>
                  <p>{selectedFinding.cvssScore.toFixed(1)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">状态</label>
                  <Badge className={getFindingStatusColor(selectedFinding.status)}>{selectedFinding.status}</Badge>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">发现时间</label>
                  <p>{new Date(selectedFinding.discoveredAt).toLocaleString()}</p>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">描述</label>
                <p className="mt-1 p-3 bg-gray-100 dark:bg-gray-800 rounded text-sm">{selectedFinding.description}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">影响</label>
                <p className="mt-1 p-3 bg-red-50 dark:bg-red-900/20 rounded text-sm">{selectedFinding.impact}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">修复建议</label>
                <p className="mt-1 p-3 bg-green-50 dark:bg-green-900/20 rounded text-sm">{selectedFinding.remediation}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">证明</label>
                <pre className="mt-1 p-3 bg-gray-100 dark:bg-gray-800 rounded text-sm overflow-auto">{selectedFinding.proof}</pre>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => setSelectedFinding(null)}>关闭</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
