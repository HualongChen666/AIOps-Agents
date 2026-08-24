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

interface RepairScript {
  id: string;
  name: string;
  description: string;
  language: 'bash' | 'python' | 'powershell' | 'javascript';
  platform: 'linux' | 'windows' | 'macos' | 'docker' | 'kubernetes';
  category: string;
  content: string;
  version: string;
  createdAt: string;
  updatedAt: string;
  author: string;
  status: 'active' | 'inactive' | 'deprecated';
}

export default function RepairScriptsPage() {
  const [scripts, setScripts] = useState<RepairScript[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedScript, setSelectedScript] = useState<RepairScript | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    language: 'bash' as RepairScript['language'],
    platform: 'linux' as RepairScript['platform'],
    category: '',
    content: '',
  });

  const loadScripts = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/scripts');
      const items = resp.data?.items || [];
      setScripts(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          name: item.name || '',
          description: item.description || '',
          language: (item.language || 'bash') as RepairScript['language'],
          platform: (item.platform || 'linux') as RepairScript['platform'],
          category: item.category || '',
          content: item.content || '',
          version: item.version || '1.0.0',
          createdAt: item.created_at || new Date().toISOString(),
          updatedAt: item.updated_at || new Date().toISOString(),
          author: item.author || 'System',
          status: (item.status || 'active') as RepairScript['status'],
        }))
      );
    } catch (err: any) {
      console.error('加载修复脚本失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScripts();
  }, []);

  const handleCreateScript = async () => {
    try {
      await api.post('/api/v1/repair/scripts', formData);
      setIsCreateDialogOpen(false);
      setFormData({ name: '', description: '', language: 'bash', platform: 'linux', category: '', content: '' });
      await loadScripts();
    } catch (err: any) {
      console.error('创建脚本失败:', err);
      setError(err.message || '创建失败');
    }
  };

  const handleDeleteScript = async (scriptId: string) => {
    try {
      await api.delete(`/api/v1/repair/scripts/${scriptId}`);
      await loadScripts();
    } catch (err: any) {
      console.error('删除脚本失败:', err);
      setError(err.message || '删除失败');
    }
  };

  const handleToggleStatus = async (scriptId: string, currentStatus: string) => {
    try {
      await api.patch(`/api/v1/repair/scripts/${scriptId}`, {
        status: currentStatus === 'active' ? 'inactive' : 'active'
      });
      await loadScripts();
    } catch (err: any) {
      console.error('更新状态失败:', err);
      setError(err.message || '更新失败');
    }
  };

  const getLanguageColor = (language: string) => {
    switch (language) {
      case 'bash':
        return 'bg-green-100 text-green-800';
      case 'python':
        return 'bg-blue-100 text-blue-800';
      case 'powershell':
        return 'bg-purple-100 text-purple-800';
      case 'javascript':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'deprecated':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">修复脚本</h1>
        <div className="flex gap-2">
          <Button onClick={loadScripts} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            创建脚本
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 脚本列表 */}
      <Card>
        <CardHeader>
          <CardTitle>修复脚本库</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : scripts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无脚本</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>语言</TableHead>
                  <TableHead>平台</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>作者</TableHead>
                  <TableHead>更新时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {scripts.map((script) => (
                  <TableRow key={script.id}>
                    <TableCell className="font-mono text-sm">{script.id}</TableCell>
                    <TableCell className="font-medium">{script.name}</TableCell>
                    <TableCell className="max-w-xs truncate">{script.description}</TableCell>
                    <TableCell>
                      <Badge className={getLanguageColor(script.language)}>
                        {script.language}
                      </Badge>
                    </TableCell>
                    <TableCell>{script.platform}</TableCell>
                    <TableCell>{script.category}</TableCell>
                    <TableCell className="font-mono text-sm">{script.version}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(script.status)}>
                        {script.status === 'active' ? '活跃' :
                         script.status === 'inactive' ? '停用' : '已废弃'}
                      </Badge>
                    </TableCell>
                    <TableCell>{script.author}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(script.updatedAt).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedScript(script)}
                        >
                          查看
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleStatus(script.id, script.status)}
                        >
                          {script.status === 'active' ? '停用' : '启用'}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteScript(script.id)}
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

      {/* 查看脚本弹窗 */}
      {selectedScript && (
        <Dialog open={!!selectedScript} onOpenChange={() => setSelectedScript(null)}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{selectedScript.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">描述</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedScript.description}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">版本</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedScript.version}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">语言</label>
                  <Badge className={getLanguageColor(selectedScript.language)}>
                    {selectedScript.language}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">平台</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedScript.platform}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">脚本内容</label>
                <pre className="mt-1 p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-sm">
                  {selectedScript.content}
                </pre>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => setSelectedScript(null)}>关闭</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* 创建脚本弹窗 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>创建修复脚本</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">脚本名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入脚本名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入脚本描述"
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">语言</label>
                <Select value={formData.language} onValueChange={(value: any) => setFormData({ ...formData, language: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bash">Bash</SelectItem>
                    <SelectItem value="python">Python</SelectItem>
                    <SelectItem value="powershell">PowerShell</SelectItem>
                    <SelectItem value="javascript">JavaScript</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">平台</label>
                <Select value={formData.platform} onValueChange={(value: any) => setFormData({ ...formData, platform: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="linux">Linux</SelectItem>
                    <SelectItem value="windows">Windows</SelectItem>
                    <SelectItem value="macos">macOS</SelectItem>
                    <SelectItem value="docker">Docker</SelectItem>
                    <SelectItem value="kubernetes">Kubernetes</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">分类</label>
              <Input
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                placeholder="输入分类"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">脚本内容</label>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="输入脚本代码"
                rows={10}
                className="font-mono text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateScript}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
