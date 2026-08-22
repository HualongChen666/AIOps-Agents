'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Settings, Server, Database, Shield, Trash2, Edit, Plus } from 'lucide-react';

interface Settings {
  system_name?: string;
  timezone?: string;
  language?: string;
  data_retention?: string;
}

interface Asset {
  id: number;
  name: string;
  service?: string;
  business_unit?: string;
  env?: string;
  owner?: string;
  created_at?: string;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'assets'>('general');

  const [settings, setSettings] = useState<Settings>({});
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  const [showAssetDialog, setShowAssetDialog] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const [assetForm, setAssetForm] = useState({
    name: '',
    service: '',
    business_unit: '',
    env: '',
    owner: '',
  });

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      setLoading(true);
      try {
        const [settingsRes, assetsRes] = await Promise.all([
          api.get('/api/settings/'),
          api.get('/api/v1/assets/'),
        ]);
        if (!mounted) return;
        setSettings(settingsRes.data?.settings || {});
        setAssets(assetsRes.data || []);
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, []);

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const response = await api.put('/api/settings/', settings);
      setSettings(response.data?.settings || {});
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSavingSettings(false);
    }
  };

  const handleCreateAsset = async () => {
    try {
      const response = await api.post('/api/v1/assets/', assetForm);
      setAssets([...assets, response.data]);
      setShowAssetDialog(false);
      setAssetForm({ name: '', service: '', business_unit: '', env: '', owner: '' });
    } catch (error) {
      console.error('Failed to create asset:', error);
    }
  };

  const handleUpdateAsset = async () => {
    if (!editingAsset) return;
    try {
      const response = await api.put(`/api/v1/assets/${editingAsset.id}`, assetForm);
      setAssets(assets.map(a => a.id === editingAsset.id ? response.data : a));
      setShowAssetDialog(false);
      setEditingAsset(null);
      setAssetForm({ name: '', service: '', business_unit: '', env: '', owner: '' });
    } catch (error) {
      console.error('Failed to update asset:', error);
    }
  };

  const handleDeleteAsset = async (asset: Asset) => {
    if (!window.confirm(`确定要删除资产 ${asset.name} 吗？`)) return;
    try {
      await api.delete(`/api/v1/assets/${asset.id}`);
      setAssets(assets.filter(a => a.id !== asset.id));
    } catch (error) {
      console.error('Failed to delete asset:', error);
    }
  };

  const openAssetDialog = (asset?: Asset) => {
    if (asset) {
      setEditingAsset(asset);
      setAssetForm({
        name: asset.name,
        service: asset.service || '',
        business_unit: asset.business_unit || '',
        env: asset.env || '',
        owner: asset.owner || '',
      });
    } else {
      setEditingAsset(null);
      setAssetForm({ name: '', service: '', business_unit: '', env: '', owner: '' });
    }
    setShowAssetDialog(true);
  };

  const tabs = [
    { key: 'general' as const, label: '通用设置', icon: Settings },
    { key: 'assets' as const, label: '资产管理', icon: Server },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="h-8 w-8 text-[var(--accent-cyan)]" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">系统设置</h1>
          <p className="text-sm text-gray-500">管理系统配置和资产信息</p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-[var(--accent-blue)] text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {activeTab === 'general' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              通用设置
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">系统名称</label>
                <Input
                  value={settings.system_name || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, system_name: e.target.value }))}
                  placeholder="AIOps Agent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">时区</label>
                <Select
                  value={settings.timezone || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, timezone: e.target.value }))}
                >
                  <option value="">请选择</option>
                  <option value="Asia/Shanghai">Asia/Shanghai</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">语言</label>
                <Select
                  value={settings.language || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, language: e.target.value }))}
                >
                  <option value="">请选择</option>
                  <option value="zh-CN">简体中文</option>
                  <option value="en-US">English</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">数据保留期</label>
                <Select
                  value={settings.data_retention || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, data_retention: e.target.value }))}
                >
                  <option value="">请选择</option>
                  <option value="7d">7天</option>
                  <option value="30d">30天</option>
                  <option value="90d">90天</option>
                  <option value="1y">1年</option>
                </Select>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleSaveSettings} disabled={loading || savingSettings}>
                  {savingSettings ? '保存中...' : '保存设置'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'assets' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                资产管理
              </CardTitle>
              <Button onClick={() => openAssetDialog()}>
                <Plus className="h-4 w-4 mr-2" />
                添加资产
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-gray-500">加载中...</p>
            ) : assets.length === 0 ? (
              <p className="text-sm text-gray-500">暂无资产数据</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead>服务</TableHead>
                    <TableHead>业务单元</TableHead>
                    <TableHead>环境</TableHead>
                    <TableHead>负责人</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assets.map((asset) => (
                    <TableRow key={asset.id}>
                      <TableCell className="font-mono text-sm">{asset.id}</TableCell>
                      <TableCell className="font-medium">{asset.name}</TableCell>
                      <TableCell>{asset.service || '-'}</TableCell>
                      <TableCell>{asset.business_unit || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={asset.env === 'prod' ? 'destructive' : 'outline'}>
                          {asset.env || '-'}
                        </Badge>
                      </TableCell>
                      <TableCell>{asset.owner || '-'}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {asset.created_at ? new Date(asset.created_at).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => openAssetDialog(asset)}>
                            <Edit className="h-4 w-4 mr-1" />
                            编辑
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => handleDeleteAsset(asset)}>
                            <Trash2 className="h-4 w-4 mr-1" />
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
      )}

      <Dialog open={showAssetDialog} onOpenChange={setShowAssetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              {editingAsset ? '编辑资产' : '添加资产'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">资产名称</label>
              <Input
                value={assetForm.name}
                onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })}
                placeholder="输入资产名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
              <Input
                value={assetForm.service}
                onChange={(e) => setAssetForm({ ...assetForm, service: e.target.value })}
                placeholder="输入服务名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">业务单元</label>
              <Input
                value={assetForm.business_unit}
                onChange={(e) => setAssetForm({ ...assetForm, business_unit: e.target.value })}
                placeholder="输入业务单元"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">环境</label>
              <Select
                value={assetForm.env}
                onChange={(e) => setAssetForm({ ...assetForm, env: e.target.value })}
              >
                <option value="">请选择</option>
                <option value="dev">开发环境</option>
                <option value="test">测试环境</option>
                <option value="staging">预发布环境</option>
                <option value="prod">生产环境</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">负责人</label>
              <Input
                value={assetForm.owner}
                onChange={(e) => setAssetForm({ ...assetForm, owner: e.target.value })}
                placeholder="输入负责人"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssetDialog(false)}>
              取消
            </Button>
            <Button onClick={editingAsset ? handleUpdateAsset : handleCreateAsset}>
              {editingAsset ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
