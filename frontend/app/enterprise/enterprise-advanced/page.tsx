'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Tenant {
  tenant_id: string;
  name: string;
  domain: string;
  plan: string;
  max_users: number;
  status: string;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface User {
  user_id: string;
  tenant_id: string;
  username: string;
  email: string;
  full_name: string;
  role_id: string | null;
  status: string;
  attributes: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface Role {
  role_id: string;
  tenant_id: string;
  name: string;
  description: string;
  permissions: string[];
  is_system_role: boolean;
  created_at: string;
  updated_at: string;
}

interface Permission {
  permission_id: string;
  name: string;
  resource: string;
  action: string;
  description: string;
  created_at: string;
  updated_at: string;
}

interface AuditLog {
  entry_id: string;
  tenant_id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  outcome: string;
  ip_address: string;
  user_agent: string;
  timestamp: string;
  data_classification: string;
  metadata: Record<string, any>;
}

interface EnterpriseSettings {
  tenant_isolation_enabled: boolean;
  audit_retention_days: number;
  encryption_enabled: boolean;
  sso_enabled: boolean;
  compliance_standards: string[];
  custom_settings: Record<string, any>;
}

type TabType = 'tenants' | 'users' | 'roles' | 'permissions' | 'audit' | 'settings';

export default function EnterpriseAdvancedPage() {
  const [activeTab, setActiveTab] = useState<TabType>('tenants');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [settings, setSettings] = useState<EnterpriseSettings | null>(null);

  // Form states
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState<Record<string, any>>({});

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      switch (activeTab) {
        case 'tenants':
          await fetchTenants();
          break;
        case 'users':
          await fetchUsers();
          break;
        case 'roles':
          await fetchRoles();
          break;
        case 'permissions':
          await fetchPermissions();
          break;
        case 'audit':
          await fetchAuditLogs();
          break;
        case 'settings':
          await fetchSettings();
          break;
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchTenants = async () => {
    const res = await api.get('/api/v1/enterprise/tenants');
    setTenants(res.data.data?.tenants || []);
  };

  const fetchUsers = async () => {
    const res = await api.get('/api/v1/enterprise/users');
    setUsers(res.data.data?.users || []);
  };

  const fetchRoles = async () => {
    const res = await api.get('/api/v1/enterprise/roles');
    setRoles(res.data.data?.roles || []);
  };

  const fetchPermissions = async () => {
    const res = await api.get('/api/v1/enterprise/permissions');
    setPermissions(res.data.data?.permissions || []);
  };

  const fetchAuditLogs = async () => {
    const res = await api.get('/api/v1/enterprise/audit-logs');
    setAuditLogs(res.data.data?.logs || []);
  };

  const fetchSettings = async () => {
    const res = await api.get('/api/v1/enterprise/settings');
    setSettings(res.data.data);
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      let endpoint = '';
      let data = formData;

      switch (activeTab) {
        case 'tenants':
          endpoint = '/api/v1/enterprise/tenants';
          break;
        case 'users':
          endpoint = '/api/v1/enterprise/users';
          break;
        case 'roles':
          endpoint = '/api/v1/enterprise/roles';
          break;
        case 'permissions':
          endpoint = '/api/v1/enterprise/permissions';
          break;
        default:
          return;
      }

      await api.post(endpoint, data);
      setShowCreateForm(false);
      setFormData({});
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSettings = async () => {
    try {
      setLoading(true);
      await api.patch('/api/v1/enterprise/settings', formData);
      setFormData({});
      await fetchSettings();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新设置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除吗？')) return;

    try {
      setLoading(true);
      let endpoint = '';

      switch (activeTab) {
        case 'tenants':
          endpoint = `/api/v1/enterprise/tenants/${id}`;
          break;
        default:
          return;
      }

      await api.delete(endpoint);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !tenants.length && !users.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级企业功能</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {(['tenants', 'users', 'roles', 'permissions', 'audit', 'settings'] as TabType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              {activeTab === 'tenants' && '租户管理'}
              {activeTab === 'users' && '用户管理'}
              {activeTab === 'roles' && '角色管理'}
              {activeTab === 'permissions' && '权限管理'}
              {activeTab === 'audit' && '审计日志'}
              {activeTab === 'settings' && '企业设置'}
            </CardTitle>
            {activeTab !== 'audit' && activeTab !== 'settings' && (
              <Button onClick={() => setShowCreateForm(true)}>创建</Button>
            )}
            {activeTab === 'settings' && (
              <Button onClick={handleUpdateSettings}>更新设置</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : (
            <div className="space-y-4">
              {/* Tenants List */}
              {activeTab === 'tenants' && tenants.map((tenant) => (
                <div key={tenant.tenant_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{tenant.name}</h3>
                      <div className="text-sm text-gray-500">{tenant.domain}</div>
                      <div className="text-sm text-gray-500">计划: {tenant.plan}</div>
                      <div className="text-sm text-gray-500">最大用户数: {tenant.max_users}</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={tenant.status === 'active' ? 'default' : 'secondary'}>
                        {tenant.status}
                      </Badge>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(tenant.tenant_id)}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Users List */}
              {activeTab === 'users' && users.map((user) => (
                <div key={user.user_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{user.full_name}</h3>
                      <div className="text-sm text-gray-500">{user.username}</div>
                      <div className="text-sm text-gray-500">{user.email}</div>
                      <div className="text-sm text-gray-500">租户ID: {user.tenant_id}</div>
                    </div>
                    <Badge variant={user.status === 'active' ? 'default' : 'secondary'}>
                      {user.status}
                    </Badge>
                  </div>
                </div>
              ))}

              {/* Roles List */}
              {activeTab === 'roles' && roles.map((role) => (
                <div key={role.role_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{role.name}</h3>
                      <div className="text-sm text-gray-500">{role.description}</div>
                      <div className="text-sm text-gray-500">租户ID: {role.tenant_id}</div>
                      <div className="text-sm text-gray-500">权限数: {role.permissions.length}</div>
                    </div>
                    {role.is_system_role && <Badge variant="secondary">系统角色</Badge>}
                  </div>
                </div>
              ))}

              {/* Permissions List */}
              {activeTab === 'permissions' && permissions.map((perm) => (
                <div key={perm.permission_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{perm.name}</h3>
                      <div className="text-sm text-gray-500">{perm.description}</div>
                      <div className="text-sm text-gray-500">资源: {perm.resource}</div>
                      <div className="text-sm text-gray-500">操作: {perm.action}</div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Audit Logs */}
              {activeTab === 'audit' && auditLogs.map((log) => (
                <div key={log.entry_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{log.action}</h3>
                      <div className="text-sm text-gray-500">用户: {log.user_id}</div>
                      <div className="text-sm text-gray-500">租户: {log.tenant_id}</div>
                      <div className="text-sm text-gray-500">资源: {log.resource_type}/{log.resource_id}</div>
                      <div className="text-sm text-gray-500">时间: {new Date(log.timestamp).toLocaleString()}</div>
                    </div>
                    <Badge variant={log.outcome === 'success' ? 'default' : 'destructive'}>
                      {log.outcome}
                    </Badge>
                  </div>
                </div>
              ))}

              {/* Settings */}
              {activeTab === 'settings' && settings && (
                <div className="space-y-4">
                  <div className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">租户隔离</h3>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={settings.tenant_isolation_enabled}
                        onChange={(e) => setFormData({ ...formData, tenant_isolation_enabled: e.target.checked })}
                        className="rounded"
                      />
                      <label>启用租户隔离</label>
                    </div>
                  </div>

                  <div className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">审计日志保留</h3>
                    <div className="flex items-center space-x-2">
                      <input
                        type="number"
                        value={formData.audit_retention_days ?? settings.audit_retention_days}
                        onChange={(e) => setFormData({ ...formData, audit_retention_days: parseInt(e.target.value) })}
                        className="border rounded px-2 py-1 w-24"
                      />
                      <label>天</label>
                    </div>
                  </div>

                  <div className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">加密</h3>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.encryption_enabled ?? settings.encryption_enabled}
                        onChange={(e) => setFormData({ ...formData, encryption_enabled: e.target.checked })}
                        className="rounded"
                      />
                      <label>启用加密</label>
                    </div>
                  </div>

                  <div className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">单点登录 (SSO)</h3>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.sso_enabled ?? settings.sso_enabled}
                        onChange={(e) => setFormData({ ...formData, sso_enabled: e.target.checked })}
                        className="rounded"
                      />
                      <label>启用SSO</label>
                    </div>
                  </div>

                  <div className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">合规标准</h3>
                    <div className="text-sm text-gray-500">
                      {settings.compliance_standards.join(', ')}
                    </div>
                  </div>
                </div>
              )}

              {/* Empty State */}
              {activeTab === 'tenants' && tenants.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无租户</div>
              )}
              {activeTab === 'users' && users.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无用户</div>
              )}
              {activeTab === 'roles' && roles.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无角色</div>
              )}
              {activeTab === 'permissions' && permissions.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无权限</div>
              )}
              {activeTab === 'audit' && auditLogs.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无审计日志</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">创建{activeTab}</h2>
            <div className="space-y-4">
              {activeTab === 'tenants' && (
                <>
                  <input
                    type="text"
                    placeholder="租户名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="域名"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                  />
                  <select
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
                  >
                    <option value="standard">标准计划</option>
                    <option value="enterprise">企业计划</option>
                  </select>
                  <input
                    type="number"
                    placeholder="最大用户数"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, max_users: parseInt(e.target.value) })}
                  />
                </>
              )}
              {activeTab === 'users' && (
                <>
                  <input
                    type="text"
                    placeholder="租户ID"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="用户名"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                  <input
                    type="email"
                    placeholder="邮箱"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="全名"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  />
                </>
              )}
              {activeTab === 'roles' && (
                <>
                  <input
                    type="text"
                    placeholder="租户ID"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="角色名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="描述"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </>
              )}
              {activeTab === 'permissions' && (
                <>
                  <input
                    type="text"
                    placeholder="权限名称"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="资源类型"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, resource: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="操作 (read, write, delete)"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, action: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="描述"
                    className="w-full border rounded px-3 py-2"
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </>
              )}
            </div>
            <div className="flex justify-end space-x-2 mt-6">
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>取消</Button>
              <Button onClick={handleCreate}>创建</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
