'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Server, Network, Database, HardDrive, RefreshCw, Plus, Trash2, Link, Activity, Settings, Search } from 'lucide-react';

interface AssetInventory {
  id: string;
  name: string;
  asset_type: 'server' | 'database' | 'storage' | 'network' | 'application' | 'service' | 'container' | 'virtual_machine';
  status: 'active' | 'inactive' | 'decommissioned' | 'maintenance' | 'provisioning';
  hostname?: string;
  ip_address?: string;
  location?: string;
  owner?: string;
  cost_center?: string;
  created_at: string;
  updated_at: string;
}

interface AssetRelationship {
  id: string;
  source_id: string;
  target_id: string;
  relationship_type: 'depends_on' | 'hosts' | 'connects_to' | 'contains' | 'manages' | 'backup_of';
  created_at: string;
}

interface AssetLifecycle {
  id: string;
  asset_id: string;
  stage: 'planning' | 'procurement' | 'deployment' | 'operation' | 'retirement';
  start_date: string;
  end_date?: string;
  notes?: string;
}

interface AssetDependency {
  id: string;
  asset_id: string;
  depends_on_id: string;
  dependency_type: string;
  criticality: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
}

export default function AssetsAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'inventory' | 'relationships' | 'lifecycle' | 'dependencies'>('inventory');
  const [selectedAsset, setSelectedAsset] = useState<AssetInventory | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [newAssetData, setNewAssetData] = useState({
    name: '',
    asset_type: 'server' as const,
    hostname: '',
    ip_address: '',
    location: '',
    owner: '',
    cost_center: '',
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch asset inventory
  const { data: assetInventory, isLoading: inventoryLoading, error: inventoryError, refetch: refetchInventory } = useQuery<AssetInventory[]>({
    queryKey: ['asset-inventory'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/assets/inventory');
      return resp.data.assets || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch asset relationships
  const { data: assetRelationships, isLoading: relationshipsLoading, error: relationshipsError, refetch: refetchRelationships } = useQuery<AssetRelationship[]>({
    queryKey: ['asset-relationships'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/assets/relationships');
      return resp.data.relationships || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch asset lifecycle
  const { data: assetLifecycle, isLoading: lifecycleLoading, error: lifecycleError, refetch: refetchLifecycle } = useQuery<AssetLifecycle[]>({
    queryKey: ['asset-lifecycle'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/assets/lifecycle');
      return resp.data.lifecycle || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Fetch asset dependencies
  const { data: assetDependencies, isLoading: dependenciesLoading, error: dependenciesError, refetch: refetchDependencies } = useQuery<AssetDependency[]>({
    queryKey: ['asset-dependencies'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/assets/dependencies');
      return resp.data.dependencies || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Create asset mutation
  const createAssetMutation = useMutation({
    mutationFn: async (assetData: typeof newAssetData) => {
      const resp = await api.post('/api/v1/assets/inventory', assetData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Asset created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['asset-inventory'] });
    },
    onError: (error: any) => {
      showError(`Failed to create asset: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete asset mutation
  const deleteAssetMutation = useMutation({
    mutationFn: async (assetId: string) => {
      const resp = await api.delete(`/api/v1/assets/inventory/${assetId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Asset deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['asset-inventory'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete asset: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (inventoryError) {
      setPageError(inventoryError as Error);
      showError('Failed to load asset inventory');
    }
  }, [inventoryError, setPageError, showError]);

  const filteredAssets = assetInventory?.filter((asset) => {
    if (typeFilter !== 'all' && asset.asset_type !== typeFilter) return false;
    if (statusFilter !== 'all' && asset.status !== statusFilter) return false;
    if (debouncedSearch && !asset.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'decommissioned':
        return 'bg-red-100 text-red-800';
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800';
      case 'provisioning':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'server':
        return <Server className="h-4 w-4" />;
      case 'database':
        return <Database className="h-4 w-4" />;
      case 'storage':
        return <HardDrive className="h-4 w-4" />;
      case 'network':
        return <Network className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getLifecycleColor = (stage: string) => {
    switch (stage) {
      case 'planning':
        return 'bg-purple-100 text-purple-800';
      case 'procurement':
        return 'bg-blue-100 text-blue-800';
      case 'deployment':
        return 'bg-cyan-100 text-cyan-800';
      case 'operation':
        return 'bg-green-100 text-green-800';
      case 'retirement':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCriticalityColor = (criticality: string) => {
    switch (criticality) {
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

  const handleCreateAsset = () => {
    if (!newAssetData.name) {
      showError('Please enter asset name');
      return;
    }
    createAssetMutation.mutate(newAssetData);
  };

  const handleDeleteAsset = (assetId: string) => {
    if (!window.confirm('Are you sure you want to delete this asset?')) return;
    deleteAssetMutation.mutate(assetId);
  };

  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载资产数据，请稍后重试"
          action={<Button onClick={() => refetchInventory()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchInventory()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Server className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">资产管理高级</h1>
            <p className="text-sm text-gray-500">资产清单、关系、生命周期和依赖管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchInventory()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            添加资产
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="inventory">
            <Server className="h-4 w-4 mr-2" />
            资产清单
          </TabsTrigger>
          <TabsTrigger value="relationships">
            <Link className="h-4 w-4 mr-2" />
            关系管理
          </TabsTrigger>
          <TabsTrigger value="lifecycle">
            <Activity className="h-4 w-4 mr-2" />
            生命周期
          </TabsTrigger>
          <TabsTrigger value="dependencies">
            <Network className="h-4 w-4 mr-2" />
            依赖分析
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inventory" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  资产清单
                </span>
                <div className="flex gap-2">
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                    <Input
                      placeholder="搜索资产..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-64 pl-8"
                    />
                  </div>
                  <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                    <option value="all">全部类型</option>
                    <option value="server">服务器</option>
                    <option value="database">数据库</option>
                    <option value="storage">存储</option>
                    <option value="network">网络</option>
                    <option value="application">应用</option>
                    <option value="service">服务</option>
                    <option value="container">容器</option>
                    <option value="virtual_machine">虚拟机</option>
                  </Select>
                  <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">全部状态</option>
                    <option value="active">活跃</option>
                    <option value="inactive">非活跃</option>
                    <option value="maintenance">维护中</option>
                    <option value="provisioning">配置中</option>
                    <option value="decommissioned">已退役</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {inventoryLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredAssets.length === 0 ? (
                <EmptyState
                  title="没有资产"
                  description="点击添加资产开始管理"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>添加资产</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>主机名</TableHead>
                      <TableHead>IP地址</TableHead>
                      <TableHead>位置</TableHead>
                      <TableHead>所有者</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAssets.map((asset) => (
                      <TableRow key={asset.id}>
                        <TableCell className="font-mono text-sm">{asset.id}</TableCell>
                        <TableCell className="font-medium">{asset.name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getTypeIcon(asset.asset_type)}
                            <span className="capitalize">{asset.asset_type}</span>
                          </div>
                        </TableCell>
                        <TableCell>{asset.hostname || '-'}</TableCell>
                        <TableCell className="font-mono text-sm">{asset.ip_address || '-'}</TableCell>
                        <TableCell>{asset.location || '-'}</TableCell>
                        <TableCell>{asset.owner || '-'}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(asset.status)}>
                            {asset.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(asset.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedAsset(asset)}
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteAsset(asset.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="relationships" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Link className="h-5 w-5" />
                资产关系
              </CardTitle>
            </CardHeader>
            <CardContent>
              {relationshipsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !assetRelationships || assetRelationships.length === 0 ? (
                <EmptyState title="无关系数据" description="暂无资产关系记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>源资产ID</TableHead>
                      <TableHead>目标资产ID</TableHead>
                      <TableHead>关系类型</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {assetRelationships.map((rel) => (
                      <TableRow key={rel.id}>
                        <TableCell className="font-mono text-sm">{rel.id}</TableCell>
                        <TableCell className="font-mono text-sm">{rel.source_id}</TableCell>
                        <TableCell className="font-mono text-sm">{rel.target_id}</TableCell>
                        <TableCell className="capitalize">{rel.relationship_type.replace('_', ' ')}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(rel.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            编辑
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="lifecycle" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                资产生命周期
              </CardTitle>
            </CardHeader>
            <CardContent>
              {lifecycleLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !assetLifecycle || assetLifecycle.length === 0 ? (
                <EmptyState title="无生命周期数据" description="暂无资产生命周期记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资产ID</TableHead>
                      <TableHead>阶段</TableHead>
                      <TableHead>开始日期</TableHead>
                      <TableHead>结束日期</TableHead>
                      <TableHead>备注</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {assetLifecycle.map((lifecycle) => (
                      <TableRow key={lifecycle.id}>
                        <TableCell className="font-mono text-sm">{lifecycle.id}</TableCell>
                        <TableCell className="font-mono text-sm">{lifecycle.asset_id}</TableCell>
                        <TableCell>
                          <Badge className={getLifecycleColor(lifecycle.stage)}>
                            {lifecycle.stage}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(lifecycle.start_date).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {lifecycle.end_date ? new Date(lifecycle.end_date).toLocaleString() : '-'}
                        </TableCell>
                        <TableCell>{lifecycle.notes || '-'}</TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            编辑
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dependencies" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                资产依赖
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dependenciesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !assetDependencies || assetDependencies.length === 0 ? (
                <EmptyState title="无依赖数据" description="暂无资产依赖记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>资产ID</TableHead>
                      <TableHead>依赖资产ID</TableHead>
                      <TableHead>依赖类型</TableHead>
                      <TableHead>关键性</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {assetDependencies.map((dep) => (
                      <TableRow key={dep.id}>
                        <TableCell className="font-mono text-sm">{dep.id}</TableCell>
                        <TableCell className="font-mono text-sm">{dep.asset_id}</TableCell>
                        <TableCell className="font-mono text-sm">{dep.depends_on_id}</TableCell>
                        <TableCell>{dep.dependency_type}</TableCell>
                        <TableCell>
                          <Badge className={getCriticalityColor(dep.criticality)}>
                            {dep.criticality}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(dep.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            编辑
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加资产</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">资产名称</label>
              <Input
                value={newAssetData.name}
                onChange={(e) => setNewAssetData({ ...newAssetData, name: e.target.value })}
                placeholder="输入资产名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">资产类型</label>
              <Select
                value={newAssetData.asset_type}
                onChange={(e) => setNewAssetData({ ...newAssetData, asset_type: e.target.value as any })}
              >
                <option value="server">服务器</option>
                <option value="database">数据库</option>
                <option value="storage">存储</option>
                <option value="network">网络</option>
                <option value="application">应用</option>
                <option value="service">服务</option>
                <option value="container">容器</option>
                <option value="virtual_machine">虚拟机</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">主机名</label>
              <Input
                value={newAssetData.hostname}
                onChange={(e) => setNewAssetData({ ...newAssetData, hostname: e.target.value })}
                placeholder="主机名"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">IP地址</label>
              <Input
                value={newAssetData.ip_address}
                onChange={(e) => setNewAssetData({ ...newAssetData, ip_address: e.target.value })}
                placeholder="IP地址"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">位置</label>
              <Input
                value={newAssetData.location}
                onChange={(e) => setNewAssetData({ ...newAssetData, location: e.target.value })}
                placeholder="位置"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">所有者</label>
              <Input
                value={newAssetData.owner}
                onChange={(e) => setNewAssetData({ ...newAssetData, owner: e.target.value })}
                placeholder="所有者"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">成本中心</label>
              <Input
                value={newAssetData.cost_center}
                onChange={(e) => setNewAssetData({ ...newAssetData, cost_center: e.target.value })}
                placeholder="成本中心"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateAsset} disabled={createAssetMutation.isPending}>
              {createAssetMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
