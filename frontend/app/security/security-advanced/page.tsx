'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Key, Shield, Lock, AlertTriangle, FileText, Eye, EyeOff, Award } from 'lucide-react'
import toast from 'react-hot-toast'

interface SecurityKey {
  id: string
  name: string
  type: string
  status: string
  algorithm: string
  keySize: number
  usage: string[]
  createdAt: string
  expiresAt: string | null
}

interface RBACRole {
  id: string
  name: string
  description: string
  permissions: string[]
  createdAt: string
  updatedAt: string
}

interface ABACPolicy {
  id: string
  name: string
  description: string
  conditions: Record<string, any>
  effect: string
  createdAt: string
  updatedAt: string
}

interface RateLimitRule {
  id: string
  name: string
  endpoint: string
  requestsPerMinute: number
  burstSize: number
  enabled: boolean
  createdAt: string
}

interface SecurityCertificate {
  id: string
  name: string
  type: string
  issuer: string
  subject: string
  validFrom: string
  validTo: string
  status: string
}

export default function SecurityAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('keys')
  const [isCreating, setIsCreating] = useState(false)
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({})
  const [newKey, setNewKey] = useState({
    name: '',
    type: 'api_key',
    algorithm: 'RSA',
    keySize: 2048,
    usage: []
  })

  // 获取密钥列表
  const { data: keys, isLoading: keysLoading, refetch: refetchKeys } = useQuery({
    queryKey: ['security-keys'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/key-management/keys')
      return resp.data as SecurityKey[]
    }
  })

  // 获取RBAC角色
  const { data: roles, isLoading: rolesLoading, refetch: refetchRoles } = useQuery({
    queryKey: ['security-roles'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/rbac/roles')
      return resp.data as RBACRole[]
    }
  })

  // 获取ABAC策略
  const { data: policies, isLoading: policiesLoading, refetch: refetchPolicies } = useQuery({
    queryKey: ['security-policies'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/abac/policies')
      return resp.data as ABACPolicy[]
    }
  })

  // 获取速率限制规则
  const { data: rateLimits, isLoading: rateLimitsLoading, refetch: refetchRateLimits } = useQuery({
    queryKey: ['security-rate-limits'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/rate-limiting/rules')
      return resp.data as RateLimitRule[]
    }
  })

  // 获取证书
  const { data: certificates, isLoading: certificatesLoading, refetch: refetchCertificates } = useQuery({
    queryKey: ['security-certificates'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/security/certificates')
      return resp.data as SecurityCertificate[]
    }
  })

  // 创建密钥
  const createKeyMutation = useMutation({
    mutationFn: async (key: any) => {
      const resp = await api.post('/api/v1/security/key-management/keys', key)
      return resp.data
    },
    onSuccess: () => {
      toast.success('密钥创建成功')
      setIsCreating(false)
      setNewKey({ name: '', type: 'api_key', algorithm: 'RSA', keySize: 2048, usage: [] })
      refetchKeys()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除密钥
  const deleteKeyMutation = useMutation({
    mutationFn: async (keyId: string) => {
      const resp = await api.delete(`/api/v1/security/key-management/keys/${keyId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('密钥删除成功')
      refetchKeys()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 切换速率限制
  const toggleRateLimitMutation = useMutation({
    mutationFn: async ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) => {
      const resp = await api.patch(`/api/v1/security/rate-limiting/rules/${ruleId}`, { enabled })
      return resp.data
    },
    onSuccess: () => {
      toast.success('规则更新成功')
      refetchRateLimits()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchKeys()
    refetchRoles()
    refetchPolicies()
    refetchRateLimits()
    refetchCertificates()
  }

  const handleCreateKey = () => {
    createKeyMutation.mutate(newKey)
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'valid':
        return 'text-green-600 bg-green-50'
      case 'inactive':
      case 'expired':
      case 'revoked':
        return 'text-red-600 bg-red-50'
      case 'pending':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getKeyTypeIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'api_key':
        return <Key className="h-4 w-4" />
      case 'secret_key':
        return <Lock className="h-4 w-4" />
      case 'jwt':
        return <Shield className="h-4 w-4" />
      case 'ssh':
        return <Key className="h-4 w-4" />
      case 'certificate':
        return <Award className="h-4 w-4" />
      default:
        return <Key className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级安全管理</h1>
          <p className="text-sm text-gray-500 mt-1">密钥管理、访问控制与安全策略</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefreshAll} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新全部
          </Button>
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="flex gap-2 border-b overflow-x-auto">
        {[
          { id: 'keys', label: '密钥管理', icon: Key },
          { id: 'rbac', label: 'RBAC角色', icon: Shield },
          { id: 'abac', label: 'ABAC策略', icon: Lock },
          { id: 'rate-limit', label: '速率限制', icon: AlertTriangle },
          { id: 'certificates', label: '证书管理', icon: Award }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors whitespace-nowrap ${activeTab === tab.id
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 密钥管理 */}
      {activeTab === 'keys' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>密钥列表</span>
                <Button onClick={() => setIsCreating(true)} size="sm">
                  <Key className="h-4 w-4 mr-2" />
                  新建密钥
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {keysLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {keys?.map((key) => (
                    <div key={key.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {getKeyTypeIcon(key.type)}
                          <span className="font-medium">{key.name}</span>
                          <span className={`px-2 py-1 rounded text-xs ${getStatusColor(key.status)}`}>
                            {key.status}
                          </span>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            onClick={() => setShowSecret({ ...showSecret, [key.id]: !showSecret[key.id] })}
                            variant="ghost"
                            size="sm"
                          >
                            {showSecret[key.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </Button>
                          <Button
                            onClick={() => deleteKeyMutation.mutate(key.id)}
                            variant="ghost"
                            size="sm"
                          >
                            删除
                          </Button>
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        <span>类型: {key.type}</span>
                        <span className="ml-4">算法: {key.algorithm}</span>
                        <span className="ml-4">密钥长度: {key.keySize} bits</span>
                        <span className="ml-4">创建: {new Date(key.createdAt).toLocaleString()}</span>
                      </div>
                      {key.expiresAt && (
                        <div className="text-sm text-gray-500 mt-1">
                          过期时间: {new Date(key.expiresAt).toLocaleString()}
                        </div>
                      )}
                      {key.usage && key.usage.length > 0 && (
                        <div className="text-sm text-gray-500 mt-1">
                          用途: {key.usage.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建密钥表单 */}
          {isCreating && (
            <Card>
              <CardHeader>
                <CardTitle>创建密钥</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">密钥名称</label>
                    <Input
                      value={newKey.name}
                      onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                      placeholder="密钥名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">密钥类型</label>
                    <Select
                      value={newKey.type}
                      onChange={(e) => setNewKey({ ...newKey, type: e.target.value })}
                      className="w-full"
                    >
                      <option value="api_key">API Key</option>
                      <option value="secret_key">Secret Key</option>
                      <option value="jwt">JWT</option>
                      <option value="ssh">SSH Key</option>
                      <option value="certificate">Certificate</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">算法</label>
                    <Select
                      value={newKey.algorithm}
                      onChange={(e) => setNewKey({ ...newKey, algorithm: e.target.value })}
                      className="w-full"
                    >
                      <option value="RSA">RSA</option>
                      <option value="ECDSA">ECDSA</option>
                      <option value="Ed25519">Ed25519</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">密钥长度 (bits)</label>
                    <Input
                      type="number"
                      value={newKey.keySize}
                      onChange={(e) => setNewKey({ ...newKey, keySize: parseInt(e.target.value) })}
                      min={1024}
                      max={4096}
                      step={512}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateKey} disabled={createKeyMutation.isPending}>
                      {createKeyMutation.isPending ? '创建中...' : '创建'}
                    </Button>
                    <Button onClick={() => setIsCreating(false)} variant="outline">
                      取消
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* RBAC角色 */}
      {activeTab === 'rbac' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              RBAC 角色管理
            </CardTitle>
          </CardHeader>
          <CardContent>
            {rolesLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {roles?.map((role) => (
                  <div key={role.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{role.name}</span>
                      <span className="text-sm text-gray-500">
                        更新: {new Date(role.updatedAt).toLocaleString()}
                      </span>
                    </div>
                    {role.description && (
                      <p className="text-sm text-gray-600 mb-2">{role.description}</p>
                    )}
                    <div>
                      <div className="text-sm font-medium mb-1">权限:</div>
                      <div className="flex flex-wrap gap-2">
                        {role.permissions.map((perm, index) => (
                          <span key={index} className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs">
                            {perm}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ABAC策略 */}
      {activeTab === 'abac' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              ABAC 策略管理
            </CardTitle>
          </CardHeader>
          <CardContent>
            {policiesLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {policies?.map((policy) => (
                  <div key={policy.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{policy.name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${policy.effect === 'allow' ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                          {policy.effect}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">
                        更新: {new Date(policy.updatedAt).toLocaleString()}
                      </span>
                    </div>
                    {policy.description && (
                      <p className="text-sm text-gray-600 mb-2">{policy.description}</p>
                    )}
                    <div>
                      <div className="text-sm font-medium mb-1">条件:</div>
                      <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(policy.conditions, null, 2)}
                      </pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 速率限制 */}
      {activeTab === 'rate-limit' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              速率限制规则
            </CardTitle>
          </CardHeader>
          <CardContent>
            {rateLimitsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {rateLimits?.map((rule) => (
                  <div key={rule.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{rule.name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${rule.enabled ? 'text-green-600 bg-green-50' : 'text-gray-600 bg-gray-50'}`}>
                          {rule.enabled ? '启用' : '禁用'}
                        </span>
                      </div>
                      <Switch
                        checked={rule.enabled}
                        onCheckedChange={(checked) => toggleRateLimitMutation.mutate({ ruleId: rule.id, enabled: checked })}
                      />
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>端点: {rule.endpoint}</span>
                      <span className="ml-4">请求/分钟: {rule.requestsPerMinute}</span>
                      <span className="ml-4">突发大小: {rule.burstSize}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 证书管理 */}
      {activeTab === 'certificates' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5" />
              证书管理
            </CardTitle>
          </CardHeader>
          <CardContent>
            {certificatesLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {certificates?.map((cert) => (
                  <div key={cert.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{cert.name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(cert.status)}`}>
                          {cert.status}
                        </span>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>类型: {cert.type}</span>
                      <span className="ml-4">颁发者: {cert.issuer}</span>
                      <span className="ml-4">主题: {cert.subject}</span>
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      <span>有效期: {new Date(cert.validFrom).toLocaleString()} - {new Date(cert.validTo).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
