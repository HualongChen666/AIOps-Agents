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

interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  userCount: number;
  createdAt: string;
  status: 'active' | 'inactive';
}

interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description: string;
  category: string;
}

interface UserRole {
  id: string;
  userId: string;
  userName: string;
  roleId: string;
  roleName: string;
  assignedAt: string;
  assignedBy: string;
}

export default function RbacPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [userRoles, setUserRoles] = useState<UserRole[]>([]);
  const [activeTab, setActiveTab] = useState<'roles' | 'permissions' | 'assignments'>('roles');
  const [showAddRoleModal, setShowAddRoleModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [newRole, setNewRole] = useState({
    name: '',
    description: '',
    permissions: [] as string[],
  });
  const [newAssignment, setNewAssignment] = useState({
    userId: '',
    roleId: '',
  });

  const loadRbacData = async () => {
    setLoading(true);
    try {
      const [rolesRes, permissionsRes, assignmentsRes] = await Promise.all([
        api.get('/api/v1/security/rbac/roles'),
        api.get('/api/v1/security/rbac/permissions'),
        api.get('/api/v1/security/rbac/assignments'),
      ]);

      const rolesData = rolesRes.data?.roles || [];
      const permissionsData = permissionsRes.data?.permissions || [];
      const assignmentsData = assignmentsRes.data?.assignments || [];

      setRoles(rolesData);
      setPermissions(permissionsData);
      setUserRoles(assignmentsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddRole = async () => {
    try {
      await api.post('/api/v1/security/rbac/roles', newRole);
      success('角色添加成功');
      setShowAddRoleModal(false);
      setNewRole({ name: '', description: '', permissions: [] });
      loadRbacData();
    } catch (err) {
      showError('角色添加失败');
    }
  };

  const handleAssignRole = async () => {
    try {
      await api.post('/api/v1/security/rbac/assignments', newAssignment);
      success('角色分配成功');
      setShowAssignModal(false);
      setNewAssignment({ userId: '', roleId: '' });
      loadRbacData();
    } catch (err) {
      showError('角色分配失败');
    }
  };

  const handleRevokeRole = async (assignmentId: string) => {
    try {
      await api.delete(`/api/v1/security/rbac/assignments/${assignmentId}`);
      success('角色已撤销');
      loadRbacData();
    } catch (err) {
      showError('角色撤销失败');
    }
  };

  const handleToggleRole = async (roleId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/rbac/roles/${roleId}`, { status });
      success('角色状态更新成功');
      loadRbacData();
    } catch (err) {
      showError('角色状态更新失败');
    }
  };

  useEffect(() => {
    loadRbacData();
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
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'roles' as const, label: '角色管理' },
    { key: 'permissions' as const, label: '权限列表' },
    { key: 'assignments' as const, label: '角色分配' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">角色访问控制 (RBAC)</h1>
        <div className="flex gap-2">
          <Button onClick={loadRbacData}>刷新数据</Button>
          <Button onClick={() => setShowAddRoleModal(true)}>添加角色</Button>
          <Button onClick={() => setShowAssignModal(true)}>分配角色</Button>
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

      {/* 角色管理 */}
      {activeTab === 'roles' && (
        <Card>
          <CardHeader>
            <CardTitle>角色管理</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>权限</TableHead>
                  <TableHead>用户数</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.length > 0 ? roles.map((role) => (
                  <TableRow key={role.id}>
                    <TableCell className="font-medium">{role.name}</TableCell>
                    <TableCell>{role.description}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {role.permissions.slice(0, 3).map((perm, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{perm}</Badge>
                        ))}
                        {role.permissions.length > 3 && (
                          <Badge variant="outline" className="text-xs">+{role.permissions.length - 3}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{role.userCount}</TableCell>
                    <TableCell>{new Date(role.createdAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(role.status)}>{role.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleRole(role.id, role.status === 'active' ? 'inactive' : 'active')}
                      >
                        {role.status === 'active' ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No roles found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 权限列表 */}
      {activeTab === 'permissions' && (
        <Card>
          <CardHeader>
            <CardTitle>权限列表</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>资源</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>描述</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {permissions.length > 0 ? permissions.map((permission) => (
                  <TableRow key={permission.id}>
                    <TableCell className="font-medium">{permission.name}</TableCell>
                    <TableCell className="font-mono text-sm">{permission.resource}</TableCell>
                    <TableCell>{permission.action}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{permission.category}</Badge>
                    </TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{permission.description}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500">
                      No permissions found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 角色分配 */}
      {activeTab === 'assignments' && (
        <Card>
          <CardHeader>
            <CardTitle>角色分配</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>分配时间</TableHead>
                  <TableHead>分配人</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {userRoles.length > 0 ? userRoles.map((assignment) => (
                  <TableRow key={assignment.id}>
                    <TableCell className="font-medium">{assignment.userName}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{assignment.roleName}</Badge>
                    </TableCell>
                    <TableCell>{new Date(assignment.assignedAt).toLocaleString()}</TableCell>
                    <TableCell>{assignment.assignedBy}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRevokeRole(assignment.id)}
                      >
                        撤销
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500">
                      No role assignments found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 添加角色模态框 */}
      {showAddRoleModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加角色</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">角色名称</label>
                <Input
                  value={newRole.name}
                  onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                  placeholder="输入角色名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">描述</label>
                <Input
                  value={newRole.description}
                  onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                  placeholder="角色描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">权限 (逗号分隔)</label>
                <Input
                  value={newRole.permissions.join(',')}
                  onChange={(e) => setNewRole({ ...newRole, permissions: e.target.value.split(',').filter(p => p.trim()) })}
                  placeholder="read,write,delete"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddRoleModal(false)}>取消</Button>
                <Button onClick={handleAddRole}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 分配角色模态框 */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>分配角色</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">用户ID</label>
                <Input
                  value={newAssignment.userId}
                  onChange={(e) => setNewAssignment({ ...newAssignment, userId: e.target.value })}
                  placeholder="输入用户ID"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">角色</label>
                <Select
                  value={newAssignment.roleId}
                  onChange={(e) => setNewAssignment({ ...newAssignment, roleId: e.target.value })}
                >
                  <option value="">选择角色</option>
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>{role.name}</option>
                  ))}
                </Select>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAssignModal(false)}>取消</Button>
                <Button onClick={handleAssignRole}>分配</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
