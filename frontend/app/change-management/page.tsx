'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

interface ChangeRequest {
  id: string;
  title: string;
  type: 'infrastructure' | 'application' | 'configuration';
  status: 'pending' | 'approved' | 'rejected' | 'in-progress' | 'completed';
  requester: string;
  createdAt: string;
  scheduledDate: string;
  risk: 'low' | 'medium' | 'high';
}

interface ImpactAnalysis {
  service: string;
  impact: 'none' | 'low' | 'medium' | 'high';
  details: string;
}

export default function ChangeManagementPage() {
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedRequest, setSelectedRequest] = useState<string | null>(null);

  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([
    {
      id: 'CR-001',
      title: '升级数据库版本',
      type: 'infrastructure',
      status: 'pending',
      requester: '张三',
      createdAt: new Date().toISOString(),
      scheduledDate: '2024-02-15',
      risk: 'high',
    },
    {
      id: 'CR-002',
      title: '部署新版本API',
      type: 'application',
      status: 'approved',
      requester: '李四',
      createdAt: new Date(Date.now() - 86400000).toISOString(),
      scheduledDate: '2024-02-10',
      risk: 'medium',
    },
    {
      id: 'CR-003',
      title: '修改告警阈值',
      type: 'configuration',
      status: 'completed',
      requester: '王五',
      createdAt: new Date(Date.now() - 172800000).toISOString(),
      scheduledDate: '2024-02-05',
      risk: 'low',
    },
  ]);

  const [impactAnalysis, setImpactAnalysis] = useState<ImpactAnalysis[]>([
    { service: 'web-service', impact: 'high', details: '服务需要重启' },
    { service: 'api-gateway', impact: 'medium', details: '流量短暂中断' },
    { service: 'database', impact: 'high', details: '需要停机维护' },
  ]);

  const filteredRequests = changeRequests.filter(cr =>
    selectedStatus === 'all' || cr.status === selectedStatus
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'in-progress':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-gray-100 text-gray-800';
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">变更管理</h1>
        <Button>创建变更请求</Button>
      </div>

      {/* 变更请求统计 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">待审批</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">
              {changeRequests.filter(cr => cr.status === 'pending').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">进行中</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">
              {changeRequests.filter(cr => cr.status === 'in-progress').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {changeRequests.filter(cr => cr.status === 'completed').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高风险</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {changeRequests.filter(cr => cr.risk === 'high').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 变更请求列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>变更请求</CardTitle>
            <Select value={selectedStatus} onChange={(e) => setSelectedStatus(e.target.value)}>
              <option value="all">全部状态</option>
              <option value="pending">待审批</option>
              <option value="approved">已批准</option>
              <option value="rejected">已拒绝</option>
              <option value="in-progress">进行中</option>
              <option value="completed">已完成</option>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>风险</TableHead>
                <TableHead>申请人</TableHead>
                <TableHead>计划日期</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRequests.map((cr) => (
                <TableRow key={cr.id}>
                  <TableCell className="font-mono text-sm">{cr.id}</TableCell>
                  <TableCell className="font-medium">{cr.title}</TableCell>
                  <TableCell>
                    {cr.type === 'infrastructure' ? '基础设施' : cr.type === 'application' ? '应用' : '配置'}
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(cr.status)}>
                      {cr.status === 'pending' ? '待审批' : cr.status === 'approved' ? '已批准' : cr.status === 'rejected' ? '已拒绝' : cr.status === 'in-progress' ? '进行中' : '已完成'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getRiskColor(cr.risk)}>
                      {cr.risk === 'high' ? '高' : cr.risk === 'medium' ? '中' : '低'}
                    </Badge>
                  </TableCell>
                  <TableCell>{cr.requester}</TableCell>
                  <TableCell className="text-sm text-gray-500">{cr.scheduledDate}</TableCell>
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

      {/* 影响分析 */}
      {selectedRequest && (
        <Card>
          <CardHeader>
            <CardTitle>影响分析</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>服务</TableHead>
                  <TableHead>影响程度</TableHead>
                  <TableHead>详情</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {impactAnalysis.map((impact, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-medium">{impact.service}</TableCell>
                    <TableCell>
                      <Badge className={
                        impact.impact === 'high' ? 'bg-red-100 text-red-800' :
                        impact.impact === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        impact.impact === 'low' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }>
                        {impact.impact === 'high' ? '高' : impact.impact === 'medium' ? '中' : impact.impact === 'low' ? '低' : '无'}
                      </Badge>
                    </TableCell>
                    <TableCell>{impact.details}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 变更日历 */}
      <Card>
        <CardHeader>
          <CardTitle>变更日历</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">变更日历视图 (使用日历组件渲染)</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
