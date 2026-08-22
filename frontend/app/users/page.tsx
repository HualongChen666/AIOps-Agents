'use client';

import { useEffect, useMemo, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Users, Shield, Settings, Trash2, Edit, Key } from 'lucide-react';

interface User {
  id: number;
  username: string;
  role: string;
  is_active?: boolean;
  disabled?: boolean;
  created_at?: string;
  asset_permissions?: any;
}

interface Asset {
  id: number;
  name?: string;
}

const ROLES = [
  { value: 'viewer', label: '查看者' },
  { value: 'business', label: '业务用户' },
  { value: 'operator', label: '运维' },
  { value: 'admin', label: '管理员' },
];

function isActive(user: User) {
  return user.is_active ?? !user.disabled;
}

function formatDate(value?: string) {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString('zh-CN');
  } catch {
    return value;
  }
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);

  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'viewer' });
  const [creating, setCreating] = useState(false);

  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editForm, setEditForm] = useState({ role: '', is_active: true, password: '' });
  const [savingEdit, setSavingEdit] = useState(false);

  const [permUser, setPermUser] = useState<User | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetsLoaded, setAssetsLoaded] = useState(false);
  const [assetPerms, setAssetPerms] = useState<Record<number, 'view' | 'edit'>>({});
  const [savingPerms, setSavingPerms] = useState(false);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/v1/users');
      setUsers(res.data || []);
    } catch {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCurrentUser = async () => {
    try {
      const res = await api.get('/api/v1/auth/me');
      setCurrentUser(res.data || null);
    } catch {
      setCurrentUser(null);
    }
  };

  const loadAssets = async () => {
    if (assetsLoaded) return;
    try {
      const res = await api.get('/api/v1/assets');
      setAssets(res.data || []);
    } catch (err: any) {
      if (err?.response?.status === 404) {
        setAssets([]);
      } else {
        setAssets([]);
      }
    } finally {
      setAssetsLoaded(true);
    }
  };

  useEffect(() => {
    loadCurrentUser();
    loadUsers();
  }, []);

  const adminCount = useMemo(() => users.filter((u) => u.role === 'admin').length, [users]);

  const canCreateAdmin = adminCount < 3;
  const adminLimitWarning = newUser.role === 'admin' && adminCount >= 3;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newUser.role === 'admin' && adminCount >= 3) return;
    setCreating(true);
    try {
      await api.post('/api/v1/users', {
        username: newUser.username,
        password: newUser.password,
        role: newUser.role,
      });
      setNewUser({ username: '', password: '', role: 'viewer' });
      await loadUsers();
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (user: User) => {
    setEditingUser(user);
    setEditForm({
      role: user.role,
      is_active: isActive(user),
      password: '',
    });
  };

  const handleEditSave = async () => {
    if (!editingUser) return;
    if (editForm.role === 'admin' && editingUser.role !== 'admin' && adminCount >= 3) {
      window.alert('已达到最大 3 个管理员数量限制');
      return;
    }
    setSavingEdit(true);
    try {
      const payload: any = { role: editForm.role, is_active: editForm.is_active };
      if (editForm.password.trim()) {
        payload.new_password = editForm.password.trim();
      }
      await api.put(`/api/v1/users/${editingUser.id}`, payload);
      setEditingUser(null);
      await loadUsers();
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async (user: User) => {
    if (currentUser && user.id === currentUser.id) {
      window.alert('不能删除当前登录用户');
      return;
    }
    if (user.role === 'admin' && adminCount <= 1) {
      window.alert('不能删除最后一个管理员');
      return;
    }
    if (!window.confirm(`确定删除用户 ${user.username} 吗？此操作不可恢复。`)) return;
    try {
      await api.delete(`/api/v1/users/${user.id}`);
      await loadUsers();
    } catch {
      // API interceptor displays error via toast for non-GET requests
    }
  };

  const startPermissions = async (user: User) => {
    setPermUser(user);
    setAssetPerms({});
    await loadAssets();
    try {
      const res = await api.get(`/api/v1/users/${user.id}/permissions`);
      const perms = res.data;
      if (Array.isArray(perms)) {
        const map: Record<number, 'view' | 'edit'> = {};
        perms.forEach((p: any) => {
          const id = Number(p.asset_id);
          const level = p.permission === 'edit' ? 'edit' : 'view';
          if (!Number.isNaN(id)) map[id] = level;
        });
        setAssetPerms(map);
      }
    } catch {
      // ignore; start with empty permissions
    }
  };

  const toggleAsset = (id: number) => {
    setAssetPerms((prev) => {
      const next = { ...prev };
      if (id in next) {
        delete next[id];
      } else {
        next[id] = 'view';
      }
      return next;
    });
  };

  const changeAssetPermission = (id: number, level: 'view' | 'edit') => {
    setAssetPerms((prev) => ({ ...prev, [id]: level }));
  };

  const handleSavePermissions = async () => {
    if (!permUser) return;
    setSavingPerms(true);
    try {
      const payload = Object.entries(assetPerms).map(([id, permission]) => ({ asset_id: Number(id), permission }));
      await api.put(`/api/v1/users/${permUser.id}/permissions`, { permissions: payload });
      setPermUser(null);
      await loadUsers();
    } finally {
      setSavingPerms(false);
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return <Badge variant="destructive">管理员</Badge>;
      case 'operator':
        return <Badge variant="default">运维</Badge>;
      case 'business':
        return <Badge variant="secondary">业务用户</Badge>;
      default:
        return <Badge variant="outline">查看者</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">用户管理</h1>
            <p className="text-sm text-gray-500">管理系统用户、角色和权限</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            管理员: {adminCount}/3
          </Badge>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            创建用户
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Input
              required
              placeholder="用户名"
              value={newUser.username}
              onChange={(e) => setNewUser((p) => ({ ...p, username: e.target.value }))}
            />
            <Input
              type="password"
              required
              placeholder="密码"
              value={newUser.password}
              onChange={(e) => setNewUser((p) => ({ ...p, password: e.target.value }))}
            />
            <Select
              value={newUser.role}
              onChange={(e) => setNewUser((p) => ({ ...p, role: e.target.value }))}
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={creating || !canCreateAdmin}>
              {creating ? '创建中...' : '创建用户'}
            </Button>
          </form>
          {adminLimitWarning && (
            <p className="mt-2 text-sm text-red-600">
              已存在 {adminCount} 个管理员，无法创建更多管理员（最多 3 个）
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            用户列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-gray-500">加载中...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>用户名</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-gray-500">
                      暂无用户
                    </TableCell>
                  </TableRow>
                )}
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-mono text-sm">{user.id}</TableCell>
                    <TableCell className="font-medium">{user.username}</TableCell>
                    <TableCell>{getRoleBadge(user.role)}</TableCell>
                    <TableCell>
                      {isActive(user) ? (
                        <Badge variant="default">启用</Badge>
                      ) : (
                        <Badge variant="secondary">禁用</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">{formatDate(user.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" variant="outline" onClick={() => startEdit(user)}>
                          <Edit className="h-4 w-4 mr-1" />
                          编辑
                        </Button>
                        {user.role === 'business' && (
                          <Button size="sm" variant="outline" onClick={() => startPermissions(user)}>
                            <Shield className="h-4 w-4 mr-1" />
                            权限
                          </Button>
                        )}
                        <Button size="sm" variant="destructive" onClick={() => handleDelete(user)}>
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

      <Dialog open={!!editingUser} onOpenChange={(open) => !open && setEditingUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="h-5 w-5" />
              编辑用户: {editingUser?.username}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">角色</label>
              <Select
                value={editForm.role}
                onChange={(e) => setEditForm((p) => ({ ...p, role: e.target.value }))}
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">状态</label>
              <Select
                value={editForm.is_active ? 'true' : 'false'}
                onChange={(e) =>
                  setEditForm((p) => ({ ...p, is_active: e.target.value === 'true' }))
                }
              >
                <option value="true">启用</option>
                <option value="false">禁用</option>
              </Select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">重置密码</label>
              <Input
                type="password"
                value={editForm.password}
                onChange={(e) => setEditForm((p) => ({ ...p, password: e.target.value }))}
                placeholder="留空则不修改"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingUser(null)}>
              取消
            </Button>
            <Button onClick={handleEditSave} disabled={savingEdit}>
              {savingEdit ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!permUser} onOpenChange={(open) => !open && setPermUser(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              资产权限: {permUser?.username}
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-auto py-2">
            {!assetsLoaded ? (
              <p className="text-sm text-gray-500">加载资产中...</p>
            ) : assets.length === 0 ? (
              <p className="text-sm text-gray-500">暂无可用资产</p>
            ) : (
              <div className="space-y-2">
                {assets.map((asset) => {
                  const selected = asset.id in assetPerms;
                  return (
                    <div key={asset.id} className="flex items-center gap-4 rounded border p-3 hover:bg-gray-50 transition">
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleAsset(asset.id)}
                        className="h-4 w-4"
                      />
                      <span className="flex-1 text-sm font-medium">
                        {asset.name || `资产 ${asset.id}`}
                      </span>
                      <Select
                        value={assetPerms[asset.id] || 'view'}
                        onChange={(e) => changeAssetPermission(asset.id, e.target.value as 'view' | 'edit')}
                        disabled={!selected}
                      >
                        <option value="view">查看</option>
                        <option value="edit">编辑</option>
                      </Select>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPermUser(null)}>
              取消
            </Button>
            <Button onClick={handleSavePermissions} disabled={savingPerms || !assetsLoaded}>
              {savingPerms ? '保存中...' : '保存权限'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
