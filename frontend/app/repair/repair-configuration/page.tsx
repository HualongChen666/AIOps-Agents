'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';


interface RepairConfig {
  id: string;
  name: string;
  description: string;
  configType: 'global' | 'platform' | 'resource' | 'script';
  key: string;
  value: string;
  category: string;
  isSecret: boolean;
  isActive: boolean;
  updatedAt: string;
  updatedBy: string;
}

export default function RepairConfigurationPage() {
  const [configs, setConfigs] = useState<RepairConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [selectedConfig, setSelectedConfig] = useState<RepairConfig | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    configType: 'global' as RepairConfig['configType'],
    key: '',
    value: '',
    category: '',
    isSecret: false,
  });

  const loadConfigs = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/configuration');
      const items = resp.data?.items || [];
      setConfigs(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          name: item.name || '',
          description: item.description || '',
          configType: (item.config_type || 'global') as RepairConfig['configType'],
          key: item.key || '',
          value: item.is_secret ? '******' : (item.value || ''),
          category: item.category || '',
          isSecret: item.is_secret || false,
          isActive: item.is_active !== false,
          updatedAt: item.updated_at || new Date().toISOString(),
          updatedBy: item.updated_by || 'System',
        }))
      );
    } catch (err: any) {
      console.error('加载修复配置失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  const handleCreateConfig = async () => {
    try {
      await api.post('/api/v1/repair/configuration', formData);
      setIsCreateDialogOpen(false);
      setFormData({ name: '', description: '', configType: 'global', key: '', value: '', category: '', isSecret: false });
      await loadConfigs();
    } catch (err: any) {
      console.error('创建配置失败:', err);
      setError(err.message || '创建失败');
    }
  };

  const handleUpdateConfig = async (configId: string, updates: Partial<RepairConfig>) => {
    try {
      await api.patch(`/api/v1/repair/configuration/${configId}`, updates);
      await loadConfigs();
    } catch (err: any) {
      console.error('更新配置失败:', err);
      setError(err.message || '更新失败');
    }
  };

  const handleDeleteConfig = async (configId: string) => {
    try {
      await api.delete(`/api/v1/repair/configuration/${configId}`);
      await loadConfigs();
    } catch (err: any) {
      console.error('删除配置失败:', err);
      setError(err.message || '删除失败');
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'global': return 'bg-purple-100 text-purple-800';
      case 'platform': return 'bg-blue-100 text-blue-800';
      case 'resource': return 'bg-green-100 text-green-800';
      case 'script': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredConfigs = configs.filter((config) => {
    const matchesCategory = filterCategory === 'all' || config.category === filterCategory;
    const matchesType = filterType === 'all' || config.configType === filterType;
    return matchesCategory && matchesType;
  });

  const categories = Array.from(new Set(configs.map(c => c.category)));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">修复配置</h1>
        <div className="flex gap-2">
          <Button onClick={loadConfigs} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            创建配置
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总配置数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{configs.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">活跃配置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{configs.filter(c => c.isActive).length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">敏感配置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{configs.filter(c => c.isSecret).length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">分类数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{categories.length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap">
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="配置类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="global">全局</SelectItem>
                <SelectItem value="platform">平台</SelectItem>
                <SelectItem value="resource">资源</SelectItem>
                <SelectItem value="script">脚本</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterCategory} onValueChange={setFilterCategory}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="分类" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分类</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>修复配置列表</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredConfigs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>配置类型</TableHead>
                  <TableHead>键</TableHead>
                  <TableHead>值</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>敏感</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>更新时间</TableHead>
                  <TableHead>更新者</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredConfigs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell className="font-mono text-sm">{config.id}</TableCell>
                    <TableCell className="font-medium">{config.name}</TableCell>
                    <TableCell className="max-w-xs truncate">{config.description}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(config.configType)}>
                        {config.configType === 'global' ? '全局' :
                          config.configType === 'platform' ? '平台' :
                            config.configType === 'resource' ? '资源' : '脚本'}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{config.key}</TableCell>
                    <TableCell className="font-mono text-sm max-w-xs truncate">{config.value}</TableCell>
                    <TableCell>{config.category}</TableCell>
                    <TableCell>
                      {config.isSecret && <Badge variant="secondary">是</Badge>}
                    </TableCell>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={config.isActive}
                        onChange={(e) => handleUpdateConfig(config.id, { isActive: e.target.checked })}
                        className="w-4 h-4"
                      />
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(config.updatedAt).toLocaleString()}
                    </TableCell>
                    <TableCell>{config.updatedBy}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedConfig(config)}
                        >
                          编辑
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteConfig(config.id)}
                        >
                          删除
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

      {selectedConfig && (
        <Dialog open={!!selectedConfig} onOpenChange={() => setSelectedConfig(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>编辑配置 - {selectedConfig.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">名称</label>
                <Input value={selectedConfig.name} disabled />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">键</label>
                <Input value={selectedConfig.key} disabled />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">值</label>
                <Textarea
                  value={selectedConfig.value}
                  onChange={(e) => setSelectedConfig({ ...selectedConfig, value: e.target.value })}
                  rows={3}
                  disabled={selectedConfig.isSecret}
                />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => setSelectedConfig(null)}>关闭</Button>
              <Button onClick={() => handleUpdateConfig(selectedConfig.id, { value: selectedConfig.value })}>
                保存
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建修复配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">配置名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入配置名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入配置描述"
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">配置类型</label>
                <Select value={formData.configType} onValueChange={(value: any) => setFormData({ ...formData, configType: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="global">全局</SelectItem>
                    <SelectItem value="platform">平台</SelectItem>
                    <SelectItem value="resource">资源</SelectItem>
                    <SelectItem value="script">脚本</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">分类</label>
                <Input
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="输入分类"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">键</label>
              <Input
                value={formData.key}
                onChange={(e) => setFormData({ ...formData, key: e.target.value })}
                placeholder="输入配置键"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">值</label>
              <Textarea
                value={formData.value}
                onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                placeholder="输入配置值"
                rows={3}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.isSecret}
                onChange={(e) => setFormData({ ...formData, isSecret: e.target.checked })}
                className="w-4 h-4"
              />
              <label className="text-sm font-medium text-gray-700">敏感配置</label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateConfig}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
