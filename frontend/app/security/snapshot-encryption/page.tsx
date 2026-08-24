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

interface Snapshot {
  id: string;
  name: string;
  source: string;
  type: 'volume' | 'database' | 'filesystem';
  size: number;
  encrypted: boolean;
  encryptionAlgorithm: string;
  encryptionKeyId: string;
  createdAt: string;
  status: 'available' | 'creating' | 'deleting' | 'error';
  retentionDays: number;
}

interface EncryptionJob {
  id: string;
  snapshotId: string;
  snapshotName: string;
  operation: 'encrypt' | 'decrypt' | 'rekey';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startedAt: string;
  completedAt?: string;
  errorMessage?: string;
}

interface EncryptionPolicy {
  id: string;
  name: string;
  appliesTo: string[];
  enforceEncryption: boolean;
  algorithm: string;
  keyRotationDays: number;
  autoDeleteUnencrypted: boolean;
  createdAt: string;
  status: 'active' | 'inactive';
}

export default function SnapshotEncryptionPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [jobs, setJobs] = useState<EncryptionJob[]>([]);
  const [policies, setPolicies] = useState<EncryptionPolicy[]>([]);
  const [activeTab, setActiveTab] = useState<'snapshots' | 'jobs' | 'policies'>('snapshots');

  const loadSnapshotEncryptionData = async () => {
    setLoading(true);
    try {
      const [snapshotsRes, jobsRes, policiesRes] = await Promise.all([
        api.get('/api/v1/security/snapshot-encryption/snapshots'),
        api.get('/api/v1/security/snapshot-encryption/jobs'),
        api.get('/api/v1/security/snapshot-encryption/policies'),
      ]);

      const snapshotsData = snapshotsRes.data?.snapshots || [];
      const jobsData = jobsRes.data?.jobs || [];
      const policiesData = policiesRes.data?.policies || [];

      setSnapshots(snapshotsData);
      setJobs(jobsData);
      setPolicies(policiesData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleEncryptSnapshot = async (snapshotId: string) => {
    try {
      await api.post(`/api/v1/security/snapshot-encryption/snapshots/${snapshotId}/encrypt`);
      success('加密任务已启动');
      loadSnapshotEncryptionData();
    } catch (err) {
      showError('启动加密失败');
    }
  };

  const handleDecryptSnapshot = async (snapshotId: string) => {
    try {
      await api.post(`/api/v1/security/snapshot-encryption/snapshots/${snapshotId}/decrypt`);
      success('解密任务已启动');
      loadSnapshotEncryptionData();
    } catch (err) {
      showError('启动解密失败');
    }
  };

  const handleRekeySnapshot = async (snapshotId: string) => {
    try {
      await api.post(`/api/v1/security/snapshot-encryption/snapshots/${snapshotId}/rekey`);
      success('密钥轮换任务已启动');
      loadSnapshotEncryptionData();
    } catch (err) {
      showError('启动密钥轮换失败');
    }
  };

  const handleTogglePolicy = async (policyId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/snapshot-encryption/policies/${policyId}`, { status });
      success('策略状态更新成功');
      loadSnapshotEncryptionData();
    } catch (err) {
      showError('策略状态更新失败');
    }
  };

  useEffect(() => {
    loadSnapshotEncryptionData();
    // Auto-refresh for running jobs
    const interval = setInterval(() => {
      const hasRunningJobs = jobs.some(j => j.status === 'running');
      if (hasRunningJobs) {
        loadSnapshotEncryptionData();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [jobs]);

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
      case 'available':
      case 'completed':
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'creating':
      case 'running':
      case 'pending':
        return 'bg-blue-100 text-blue-800';
      case 'deleting':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
      case 'failed':
      case 'inactive':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'snapshots' as const, label: '快照列表' },
    { key: 'jobs' as const, label: '加密任务' },
    { key: 'policies' as const, label: '加密策略' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">快照加密</h1>
        <Button onClick={loadSnapshotEncryptionData}>刷新数据</Button>
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

      {/* 快照列表 */}
      {activeTab === 'snapshots' && (
        <Card>
          <CardHeader>
            <CardTitle>快照列表</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>大小</TableHead>
                  <TableHead>加密状态</TableHead>
                  <TableHead>算法</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>保留天数</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshots.length > 0 ? snapshots.map((snapshot) => (
                  <TableRow key={snapshot.id}>
                    <TableCell className="font-medium">{snapshot.name}</TableCell>
                    <TableCell>{snapshot.source}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{snapshot.type}</Badge>
                    </TableCell>
                    <TableCell>{(snapshot.size / 1024 / 1024 / 1024).toFixed(2)} GB</TableCell>
                    <TableCell>
                      <Badge className={snapshot.encrypted ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                        {snapshot.encrypted ? '已加密' : '未加密'}
                      </Badge>
                    </TableCell>
                    <TableCell>{snapshot.encryptionAlgorithm}</TableCell>
                    <TableCell>{new Date(snapshot.createdAt).toLocaleString()}</TableCell>
                    <TableCell>{snapshot.retentionDays} 天</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(snapshot.status)}>{snapshot.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {!snapshot.encrypted && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEncryptSnapshot(snapshot.id)}
                          >
                            加密
                          </Button>
                        )}
                        {snapshot.encrypted && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDecryptSnapshot(snapshot.id)}
                          >
                            解密
                          </Button>
                        )}
                        {snapshot.encrypted && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRekeySnapshot(snapshot.id)}
                          >
                            轮换密钥
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-gray-500">
                      No snapshots found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 加密任务 */}
      {activeTab === 'jobs' && (
        <Card>
          <CardHeader>
            <CardTitle>加密任务</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>快照</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>进度</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>完成时间</TableHead>
                  <TableHead>错误信息</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.length > 0 ? jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell className="font-medium">{job.snapshotName}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{job.operation}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(job.status)}>{job.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${job.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-sm">{job.progress}%</span>
                    </TableCell>
                    <TableCell>{new Date(job.startedAt).toLocaleString()}</TableCell>
                    <TableCell>{job.completedAt ? new Date(job.completedAt).toLocaleString() : '-'}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate text-red-600">{job.errorMessage || '-'}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No encryption jobs found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 加密策略 */}
      {activeTab === 'policies' && (
        <Card>
          <CardHeader>
            <CardTitle>加密策略</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>应用范围</TableHead>
                  <TableHead>强制加密</TableHead>
                  <TableHead>算法</TableHead>
                  <TableHead>密钥轮换周期</TableHead>
                  <TableHead>自动删除未加密</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.length > 0 ? policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell className="font-medium">{policy.name}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {policy.appliesTo.map((scope, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{scope}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={policy.enforceEncryption ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {policy.enforceEncryption ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>{policy.algorithm}</TableCell>
                    <TableCell>{policy.keyRotationDays} 天</TableCell>
                    <TableCell>
                      <Badge className={policy.autoDeleteUnencrypted ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}>
                        {policy.autoDeleteUnencrypted ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(policy.status)}>{policy.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTogglePolicy(policy.id, policy.status === 'active' ? 'inactive' : 'active')}
                      >
                        {policy.status === 'active' ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No encryption policies found
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
