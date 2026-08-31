'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Settings, CheckCircle, XCircle, Clock, Play, AlertTriangle, Wrench, Shield } from 'lucide-react'
import toast from 'react-hot-toast'

interface RepairConfig {
  id: string
  name: string
  description: string
  config_type: string
  key: string
  value: string
  category: string
  is_secret: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

interface HITLApproval {
  id: string
  repair_id: string
  requested_by: string
  request_time: string
  status: string
  approved_by: string | null
  approval_time: string | null
  rejection_reason: string | null
  risk_level: string
  description: string
}

interface RepairEffectiveness {
  id: string
  repair_id: string
  success_rate: number
  avg_duration: number
  total_repairs: number
  failed_repairs: number
  last_updated: string
}

interface RepairVerification {
  id: string
  repair_id: string
  verification_status: string
  verification_time: string
  verified_by: string
  verification_notes: string
  metrics_before: Record<string, any>
  metrics_after: Record<string, any>
}

export default function RepairAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('config')
  const [isCreating, setIsCreating] = useState(false)
  const [editingConfig, setEditingConfig] = useState<RepairConfig | null>(null)
  const [newConfig, setNewConfig] = useState({
    name: '',
    description: '',
    config_type: 'global',
    key: '',
    value: '',
    category: 'default',
    is_secret: false
  })
  const [selectedRepairId, setSelectedRepairId] = useState('')

  // 获取修复配置
  const { data: configs, isLoading: configsLoading, refetch: refetchConfigs } = useQuery({
    queryKey: ['repair-configs'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/configurations')
      return resp.data as RepairConfig[]
    }
  })

  // 获取HITL审批
  const { data: approvals, isLoading: approvalsLoading, refetch: refetchApprovals } = useQuery({
    queryKey: ['repair-approvals'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/hitl-approvals')
      return resp.data as HITLApproval[]
    }
  })

  // 获取修复效果
  const { data: effectiveness, isLoading: effectivenessLoading, refetch: refetchEffectiveness } = useQuery({
    queryKey: ['repair-effectiveness'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/effectiveness')
      return resp.data as RepairEffectiveness[]
    }
  })

  // 获取修复验证
  const { data: verifications, isLoading: verificationsLoading, refetch: refetchVerifications } = useQuery({
    queryKey: ['repair-verifications'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/verifications')
      return resp.data as RepairVerification[]
    }
  })

  // 创建配置
  const createConfigMutation = useMutation({
    mutationFn: async (config: any) => {
      const resp = await api.post('/api/v1/repair/configurations', config)
      return resp.data
    },
    onSuccess: () => {
      toast.success('配置创建成功')
      setIsCreating(false)
      setNewConfig({ name: '', description: '', config_type: 'global', key: '', value: '', category: 'default', is_secret: false })
      refetchConfigs()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新配置
  const updateConfigMutation = useMutation({
    mutationFn: async ({ configId, data }: { configId: string; data: any }) => {
      const resp = await api.put(`/api/v1/repair/configurations/${configId}`, data)
      return resp.data
    },
    onSuccess: () => {
      toast.success('配置更新成功')
      setEditingConfig(null)
      refetchConfigs()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除配置
  const deleteConfigMutation = useMutation({
    mutationFn: async (configId: string) => {
      const resp = await api.delete(`/api/v1/repair/configurations/${configId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('配置删除成功')
      refetchConfigs()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 审批操作
  const approveMutation = useMutation({
    mutationFn: async (approvalId: string) => {
      const resp = await api.post(`/api/v1/repair/hitl-approvals/${approvalId}/approve`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('审批成功')
      refetchApprovals()
    },
    onError: (error: any) => {
      toast.error(`审批失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const rejectMutation = useMutation({
    mutationFn: async ({ approvalId, reason }: { approvalId: string; reason: string }) => {
      const resp = await api.post(`/api/v1/repair/hitl-approvals/${approvalId}/reject`, { reason })
      return resp.data
    },
    onSuccess: () => {
      toast.success('已拒绝')
      refetchApprovals()
    },
    onError: (error: any) => {
      toast.error(`操作失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchConfigs()
    refetchApprovals()
    refetchEffectiveness()
    refetchVerifications()
  }

  const handleCreateConfig = () => {
    createConfigMutation.mutate(newConfig)
  }

  const handleUpdateConfig = () => {
    if (!editingConfig) return
    updateConfigMutation.mutate({
      configId: editingConfig.id,
      data: {
        name: editingConfig.name,
        description: editingConfig.description,
        config_type: editingConfig.config_type,
        key: editingConfig.key,
        value: editingConfig.value,
        category: editingConfig.category,
        is_secret: editingConfig.is_secret,
        is_active: editingConfig.is_active
      }
    })
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'approved':
      case 'passed':
      case 'verified':
        return 'text-green-600 bg-green-50'
      case 'inactive':
      case 'pending':
      case 'waiting':
        return 'text-yellow-600 bg-yellow-50'
      case 'rejected':
      case 'failed':
      case 'error':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getRiskColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'high':
        return 'text-red-600 bg-red-50'
      case 'medium':
        return 'text-yellow-600 bg-yellow-50'
      case 'low':
        return 'text-green-600 bg-green-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级修复管理</h1>
          <p className="text-sm text-gray-500 mt-1">修复配置、审批流程与效果评估</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefreshAll} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新全部
          </Button>
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="flex gap-2 border-b">
        {[
          { id: 'config', label: '修复配置', icon: Settings },
          { id: 'hitl', label: 'HITL审批', icon: Shield },
          { id: 'effectiveness', label: '效果评估', icon: CheckCircle },
          { id: 'verification', label: '修复验证', icon: Wrench }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 修复配置 */}
      {activeTab === 'config' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>修复配置列表</span>
                <Button onClick={() => setIsCreating(true)} size="sm">
                  <Settings className="h-4 w-4 mr-2" />
                  新建配置
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {configsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {configs?.map((config) => (
                    <div key={config.id} className="p-4 border rounded-lg">
                      {editingConfig?.id === config.id ? (
                        <div className="space-y-3">
                          <Input
                            value={editingConfig.name}
                            onChange={(e) => setEditingConfig({ ...editingConfig, name: e.target.value })}
                          />
                          <Input
                            value={editingConfig.description}
                            onChange={(e) => setEditingConfig({ ...editingConfig, description: e.target.value })}
                          />
                          <Input
                            value={editingConfig.key}
                            onChange={(e) => setEditingConfig({ ...editingConfig, key: e.target.value })}
                          />
                          <Input
                            value={editingConfig.value}
                            onChange={(e) => setEditingConfig({ ...editingConfig, value: e.target.value })}
                            type={editingConfig.is_secret ? 'password' : 'text'}
                          />
                          <div className="flex gap-2">
                            <Button onClick={handleUpdateConfig} size="sm">
                              保存
                            </Button>
                            <Button onClick={() => setEditingConfig(null)} variant="outline" size="sm">
                              取消
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{config.name}</span>
                              <span className={`px-2 py-1 rounded text-xs ${config.is_active ? 'text-green-600 bg-green-50' : 'text-gray-600 bg-gray-50'}`}>
                                {config.is_active ? '启用' : '禁用'}
                              </span>
                              {config.is_secret && (
                                <span className="px-2 py-1 rounded text-xs bg-purple-50 text-purple-600">
                                  密钥
                                </span>
                              )}
                            </div>
                            <div className="flex gap-2">
                              <Button onClick={() => setEditingConfig(config)} variant="ghost" size="sm">
                                编辑
                              </Button>
                              <Button
                                onClick={() => deleteConfigMutation.mutate(config.id)}
                                variant="ghost"
                                size="sm"
                              >
                                删除
                              </Button>
                            </div>
                          </div>
                          <div className="text-sm text-gray-500">
                            <span>键: {config.key}</span>
                            <span className="ml-4">类型: {config.config_type}</span>
                            <span className="ml-4">分类: {config.category}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建配置表单 */}
          {isCreating && (
            <Card>
              <CardHeader>
                <CardTitle>创建修复配置</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">配置名称</label>
                    <Input
                      value={newConfig.name}
                      onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
                      placeholder="配置名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={newConfig.description}
                      onChange={(e) => setNewConfig({ ...newConfig, description: e.target.value })}
                      placeholder="配置描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">配置类型</label>
                    <Select
                      value={newConfig.config_type}
                      onChange={(e) => setNewConfig({ ...newConfig, config_type: e.target.value })}
                      className="w-full"
                    >
                      <option value="global">全局配置</option>
                      <option value="platform">平台配置</option>
                      <option value="resource">资源配置</option>
                      <option value="script">脚本配置</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">配置键</label>
                    <Input
                      value={newConfig.key}
                      onChange={(e) => setNewConfig({ ...newConfig, key: e.target.value })}
                      placeholder="config.key"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">配置值</label>
                    <Input
                      value={newConfig.value}
                      onChange={(e) => setNewConfig({ ...newConfig, value: e.target.value })}
                      type={newConfig.is_secret ? 'password' : 'text'}
                      placeholder="配置值"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">分类</label>
                    <Input
                      value={newConfig.category}
                      onChange={(e) => setNewConfig({ ...newConfig, category: e.target.value })}
                      placeholder="default"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={newConfig.is_secret}
                      onCheckedChange={(checked) => setNewConfig({ ...newConfig, is_secret: checked })}
                    />
                    <label className="text-sm">是否为密钥</label>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateConfig} disabled={createConfigMutation.isPending}>
                      {createConfigMutation.isPending ? '创建中...' : '创建'}
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

      {/* HITL审批 */}
      {activeTab === 'hitl' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              HITL (Human-in-the-Loop) 审批流程
            </CardTitle>
          </CardHeader>
          <CardContent>
            {approvalsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {approvals?.map((approval) => (
                  <div key={approval.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{approval.repair_id}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(approval.status)}`}>
                          {approval.status}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs ${getRiskColor(approval.risk_level)}`}>
                          {approval.risk_level}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {new Date(approval.request_time).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{approval.description}</p>
                    <div className="text-sm text-gray-500 mb-2">
                      <span>请求者: {approval.requested_by}</span>
                    </div>
                    {approval.status === 'pending' && (
                      <div className="flex gap-2">
                        <Button
                          onClick={() => approveMutation.mutate(approval.id)}
                          size="sm"
                          variant="default"
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          批准
                        </Button>
                        <Button
                          onClick={() => {
                            const reason = prompt('请输入拒绝原因:')
                            if (reason) rejectMutation.mutate({ approvalId: approval.id, reason })
                          }}
                          size="sm"
                          variant="destructive"
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          拒绝
                        </Button>
                      </div>
                    )}
                    {approval.approved_by && (
                      <div className="text-sm text-gray-500">
                        <span>审批者: {approval.approved_by}</span>
                        <span className="ml-4">审批时间: {new Date(approval.approval_time!).toLocaleString()}</span>
                      </div>
                    )}
                    {approval.rejection_reason && (
                      <div className="text-sm text-red-600 mt-2">
                        拒绝原因: {approval.rejection_reason}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 效果评估 */}
      {activeTab === 'effectiveness' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              修复效果评估
            </CardTitle>
          </CardHeader>
          <CardContent>
            {effectivenessLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {effectiveness?.map((eff) => (
                  <div key={eff.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{eff.repair_id}</span>
                      <span className="text-sm text-gray-500">
                        更新: {new Date(eff.last_updated).toLocaleString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-gray-600">成功率</div>
                        <div className="text-lg font-bold text-green-600">{eff.success_rate.toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">平均耗时</div>
                        <div className="text-lg font-bold">{eff.avg_duration.toFixed(1)}s</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">总修复数</div>
                        <div className="text-lg font-bold">{eff.total_repairs}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">失败数</div>
                        <div className="text-lg font-bold text-red-600">{eff.failed_repairs}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 修复验证 */}
      {activeTab === 'verification' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              修复验证
            </CardTitle>
          </CardHeader>
          <CardContent>
            {verificationsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {verifications?.map((verif) => (
                  <div key={verif.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{verif.repair_id}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(verif.verification_status)}`}>
                          {verif.verification_status}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {new Date(verif.verification_time).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      <span>验证者: {verif.verified_by}</span>
                    </div>
                    {verif.verification_notes && (
                      <p className="text-sm text-gray-600 mb-2">{verif.verification_notes}</p>
                    )}
                    <div className="grid grid-cols-2 gap-4 mt-2">
                      <div>
                        <div className="text-sm font-medium mb-1">修复前指标</div>
                        <pre className="text-xs bg-gray-50 p-2 rounded">
                          {JSON.stringify(verif.metrics_before, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <div className="text-sm font-medium mb-1">修复后指标</div>
                        <pre className="text-xs bg-gray-50 p-2 rounded">
                          {JSON.stringify(verif.metrics_after, null, 2)}
                        </pre>
                      </div>
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
