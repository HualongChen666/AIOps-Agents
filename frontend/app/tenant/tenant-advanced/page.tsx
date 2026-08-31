'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Settings, Users, CreditCard, BarChart3, Shield, Building2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface TenantConfig {
  tenant_id: string
  name: string
  domain: string | null
  logo_url: string | null
  primary_color: string
  secondary_color: string
  custom_css: string | null
  custom_js: string | null
  branding_enabled: boolean
  sso_enabled: boolean
  sso_provider: string | null
  sso_config: Record<string, any> | null
  audit_logging_enabled: boolean
  data_retention_days: number
  created_at: string | null
  updated_at: string | null
}

interface TenantSettings {
  tenant_id: string
  timezone: string
  locale: string
  date_format: string
  time_format: string
  week_start: string
  currency: string
  notification_preferences: Record<string, any>
  ui_preferences: Record<string, any>
  created_at: string | null
  updated_at: string | null
}

interface TenantLimits {
  tenant_id: string
  plan: string
  max_users: number
  max_services: number
  max_alerts_per_month: number
  max_storage_gb: number
  max_api_calls_per_day: number
  current_users: number
  current_services: number
  current_alerts_this_month: number
  current_storage_gb: number
  current_api_calls_today: number
  reset_date: string
}

interface TenantUsage {
  tenant_id: string
  period_start: string
  period_end: string
  total_api_calls: number
  total_storage_gb: number
  total_users: number
  total_services: number
  cost_breakdown: Record<string, number>
}

interface TenantMember {
  id: string
  tenant_id: string
  user_id: string
  user_name: string
  user_email: string
  role: string
  status: string
  invited_at: string
  joined_at: string | null
}

export default function TenantAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('config')
  const [editingConfig, setEditingConfig] = useState<TenantConfig | null>(null)
  const [editingSettings, setEditingSettings] = useState<TenantSettings | null>(null)

  // 获取租户配置
  const { data: tenantConfig, isLoading: configLoading, refetch: refetchConfig } = useQuery({
    queryKey: ['tenant-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/tenant/config')
      return resp.data as TenantConfig
    }
  })

  // 获取租户设置
  const { data: tenantSettings, isLoading: settingsLoading, refetch: refetchSettings } = useQuery({
    queryKey: ['tenant-settings'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/tenant/settings')
      return resp.data as TenantSettings
    }
  })

  // 获取租户限制
  const { data: tenantLimits, isLoading: limitsLoading, refetch: refetchLimits } = useQuery({
    queryKey: ['tenant-limits'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/tenant/limits')
      return resp.data as TenantLimits
    }
  })

  // 获取租户使用情况
  const { data: tenantUsage, isLoading: usageLoading, refetch: refetchUsage } = useQuery({
    queryKey: ['tenant-usage'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/tenant/usage')
      return resp.data as TenantUsage
    }
  })

  // 获取租户成员
  const { data: tenantMembers, isLoading: membersLoading, refetch: refetchMembers } = useQuery({
    queryKey: ['tenant-members'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/tenant/members')
      return resp.data as TenantMember[]
    }
  })

  // 更新租户配置
  const updateConfigMutation = useMutation({
    mutationFn: async (config: any) => {
      const resp = await api.put('/api/v1/tenant/config', config)
      return resp.data
    },
    onSuccess: () => {
      toast.success('配置更新成功')
      setEditingConfig(null)
      refetchConfig()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新租户设置
  const updateSettingsMutation = useMutation({
    mutationFn: async (settings: any) => {
      const resp = await api.put('/api/v1/tenant/settings', settings)
      return resp.data
    },
    onSuccess: () => {
      toast.success('设置更新成功')
      setEditingSettings(null)
      refetchSettings()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchConfig()
    refetchSettings()
    refetchLimits()
    refetchUsage()
    refetchMembers()
  }

  const handleUpdateConfig = () => {
    if (!editingConfig) return
    updateConfigMutation.mutate(editingConfig)
  }

  const handleUpdateSettings = () => {
    if (!editingSettings) return
    updateSettingsMutation.mutate(editingSettings)
  }

  const getUsagePercentage = (current: number, max: number) => {
    if (max === 0) return 0
    return (current / max) * 100
  }

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级租户管理</h1>
          <p className="text-sm text-gray-500 mt-1">租户配置、限制、使用情况与成员管理</p>
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
          { id: 'config', label: '租户配置', icon: Building2 },
          { id: 'settings', label: '租户设置', icon: Settings },
          { id: 'limits', label: '资源限制', icon: BarChart3 },
          { id: 'usage', label: '使用情况', icon: CreditCard },
          { id: 'members', label: '成员管理', icon: Users }
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

      {/* 租户配置 */}
      {activeTab === 'config' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                租户配置
              </span>
              <Button onClick={() => setEditingConfig(tenantConfig || undefined)} size="sm">
                编辑
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {configLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : editingConfig ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">租户名称</label>
                  <Input
                    value={editingConfig.name}
                    onChange={(e) => setEditingConfig({ ...editingConfig, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">域名</label>
                  <Input
                    value={editingConfig.domain || ''}
                    onChange={(e) => setEditingConfig({ ...editingConfig, domain: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">主色调</label>
                    <Input
                      type="color"
                      value={editingConfig.primary_color}
                      onChange={(e) => setEditingConfig({ ...editingConfig, primary_color: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">次色调</label>
                    <Input
                      type="color"
                      value={editingConfig.secondary_color}
                      onChange={(e) => setEditingConfig({ ...editingConfig, secondary_color: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={editingConfig.branding_enabled}
                    onCheckedChange={(checked) => setEditingConfig({ ...editingConfig, branding_enabled: checked })}
                  />
                  <label className="text-sm">启用品牌定制</label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={editingConfig.sso_enabled}
                    onCheckedChange={(checked) => setEditingConfig({ ...editingConfig, sso_enabled: checked })}
                  />
                  <label className="text-sm">启用SSO</label>
                </div>
                {editingConfig.sso_enabled && (
                  <div>
                    <label className="block text-sm font-medium mb-1">SSO提供商</label>
                    <Select
                      value={editingConfig.sso_provider || ''}
                      onChange={(e) => setEditingConfig({ ...editingConfig, sso_provider: e.target.value })}
                      className="w-full"
                    >
                      <option value="">选择提供商</option>
                      <option value="okta">Okta</option>
                      <option value="azure">Azure AD</option>
                      <option value="auth0">Auth0</option>
                      <option value="saml">SAML</option>
                    </Select>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <Switch
                    checked={editingConfig.audit_logging_enabled}
                    onCheckedChange={(checked) => setEditingConfig({ ...editingConfig, audit_logging_enabled: checked })}
                  />
                  <label className="text-sm">启用审计日志</label>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">数据保留天数</label>
                  <Input
                    type="number"
                    value={editingConfig.data_retention_days}
                    onChange={(e) => setEditingConfig({ ...editingConfig, data_retention_days: parseInt(e.target.value) })}
                    min={1}
                    max={365}
                  />
                </div>
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
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">租户ID</div>
                    <div className="font-medium">{tenantConfig?.tenant_id}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">租户名称</div>
                    <div className="font-medium">{tenantConfig?.name}</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">域名</div>
                  <div className="font-medium">{tenantConfig?.domain || '未设置'}</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">主色调</div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded" style={{ backgroundColor: tenantConfig?.primary_color }} />
                      <span>{tenantConfig?.primary_color}</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">次色调</div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded" style={{ backgroundColor: tenantConfig?.secondary_color }} />
                      <span>{tenantConfig?.secondary_color}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${tenantConfig?.branding_enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
                    <span className="text-sm">品牌定制: {tenantConfig?.branding_enabled ? '启用' : '禁用'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${tenantConfig?.sso_enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
                    <span className="text-sm">SSO: {tenantConfig?.sso_enabled ? '启用' : '禁用'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${tenantConfig?.audit_logging_enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
                    <span className="text-sm">审计日志: {tenantConfig?.audit_logging_enabled ? '启用' : '禁用'}</span>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">数据保留天数</div>
                  <div className="font-medium">{tenantConfig?.data_retention_days} 天</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 租户设置 */}
      {activeTab === 'settings' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                租户设置
              </span>
              <Button onClick={() => setEditingSettings(tenantSettings || undefined)} size="sm">
                编辑
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {settingsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : editingSettings ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">时区</label>
                  <Select
                    value={editingSettings.timezone}
                    onChange={(e) => setEditingSettings({ ...editingSettings, timezone: e.target.value })}
                    className="w-full"
                  >
                    <option value="UTC">UTC</option>
                    <option value="Asia/Shanghai">Asia/Shanghai</option>
                    <option value="America/New_York">America/New_York</option>
                    <option value="Europe/London">Europe/London</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">语言</label>
                  <Select
                    value={editingSettings.locale}
                    onChange={(e) => setEditingSettings({ ...editingSettings, locale: e.target.value })}
                    className="w-full"
                  >
                    <option value="zh-CN">简体中文</option>
                    <option value="en-US">English</option>
                    <option value="ja-JP">日本語</option>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">日期格式</label>
                    <Select
                      value={editingSettings.date_format}
                      onChange={(e) => setEditingSettings({ ...editingSettings, date_format: e.target.value })}
                      className="w-full"
                    >
                      <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                      <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                      <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">时间格式</label>
                    <Select
                      value={editingSettings.time_format}
                      onChange={(e) => setEditingSettings({ ...editingSettings, time_format: e.target.value })}
                      className="w-full"
                    >
                      <option value="24h">24小时制</option>
                      <option value="12h">12小时制</option>
                    </Select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">货币</label>
                  <Select
                    value={editingSettings.currency}
                    onChange={(e) => setEditingSettings({ ...editingSettings, currency: e.target.value })}
                    className="w-full"
                  >
                    <option value="CNY">CNY (¥)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                  </Select>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleUpdateSettings} size="sm">
                    保存
                  </Button>
                  <Button onClick={() => setEditingSettings(null)} variant="outline" size="sm">
                    取消
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">时区</div>
                    <div className="font-medium">{tenantSettings?.timezone}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">语言</div>
                    <div className="font-medium">{tenantSettings?.locale}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">日期格式</div>
                    <div className="font-medium">{tenantSettings?.date_format}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">时间格式</div>
                    <div className="font-medium">{tenantSettings?.time_format}</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">货币</div>
                  <div className="font-medium">{tenantSettings?.currency}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 资源限制 */}
      {activeTab === 'limits' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              资源限制
            </CardTitle>
          </CardHeader>
          <CardContent>
            {limitsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-4">
                <div className="mb-4">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">用户数</span>
                    <span className="text-sm text-gray-600">{tenantLimits?.current_users} / {tenantLimits?.max_users}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(tenantLimits?.current_users || 0, tenantLimits?.max_users || 0))}`}
                      style={{ width: `${getUsagePercentage(tenantLimits?.current_users || 0, tenantLimits?.max_users || 0)}%` }}
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">服务数</span>
                    <span className="text-sm text-gray-600">{tenantLimits?.current_services} / {tenantLimits?.max_services}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(tenantLimits?.current_services || 0, tenantLimits?.max_services || 0))}`}
                      style={{ width: `${getUsagePercentage(tenantLimits?.current_services || 0, tenantLimits?.max_services || 0)}%` }}
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">月度告警数</span>
                    <span className="text-sm text-gray-600">{tenantLimits?.current_alerts_this_month} / {tenantLimits?.max_alerts_per_month}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(tenantLimits?.current_alerts_this_month || 0, tenantLimits?.max_alerts_per_month || 0))}`}
                      style={{ width: `${getUsagePercentage(tenantLimits?.current_alerts_this_month || 0, tenantLimits?.max_alerts_per_month || 0)}%` }}
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">存储空间 (GB)</span>
                    <span className="text-sm text-gray-600">{tenantLimits?.current_storage_gb.toFixed(2)} / {tenantLimits?.max_storage_gb} GB</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(tenantLimits?.current_storage_gb || 0, tenantLimits?.max_storage_gb || 0))}`}
                      style={{ width: `${getUsagePercentage(tenantLimits?.current_storage_gb || 0, tenantLimits?.max_storage_gb || 0)}%` }}
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">日API调用数</span>
                    <span className="text-sm text-gray-600">{tenantLimits?.current_api_calls_today} / {tenantLimits?.max_api_calls_per_day}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(tenantLimits?.current_api_calls_today || 0, tenantLimits?.max_api_calls_per_day || 0))}`}
                      style={{ width: `${getUsagePercentage(tenantLimits?.current_api_calls_today || 0, tenantLimits?.max_api_calls_per_day || 0)}%` }}
                    />
                  </div>
                </div>
                <div className="text-sm text-gray-500 mt-4">
                  <span>计划: {tenantLimits?.plan}</span>
                  <span className="ml-4">重置日期: {new Date(tenantLimits?.reset_date || '').toLocaleString()}</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 使用情况 */}
      {activeTab === 'usage' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              使用情况
            </CardTitle>
          </CardHeader>
          <CardContent>
            {usageLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">总API调用</div>
                    <div className="text-2xl font-bold">{tenantUsage?.total_api_calls.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">存储使用</div>
                    <div className="text-2xl font-bold">{tenantUsage?.total_storage_gb.toFixed(2)} GB</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">用户数</div>
                    <div className="text-2xl font-bold">{tenantUsage?.total_users}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">服务数</div>
                    <div className="text-2xl font-bold">{tenantUsage?.total_services}</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium mb-2">成本明细</div>
                  <div className="space-y-2">
                    {Object.entries(tenantUsage?.cost_breakdown || {}).map(([key, value]) => (
                      <div key={key} className="flex justify-between p-2 bg-gray-50 rounded">
                        <span className="text-sm">{key}</span>
                        <span className="text-sm font-medium">${value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  周期: {new Date(tenantUsage?.period_start || '').toLocaleString()} - {new Date(tenantUsage?.period_end || '').toLocaleString()}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 成员管理 */}
      {activeTab === 'members' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              成员管理
            </CardTitle>
          </CardHeader>
          <CardContent>
            {membersLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {tenantMembers?.map((member) => (
                  <div key={member.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{member.user_name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${member.status === 'active' ? 'text-green-600 bg-green-50' : 'text-gray-600 bg-gray-50'}`}>
                          {member.status}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">{member.role}</span>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>{member.user_email}</span>
                      <span className="ml-4">邀请: {new Date(member.invited_at).toLocaleString()}</span>
                      {member.joined_at && (
                        <span className="ml-4">加入: {new Date(member.joined_at).toLocaleString()}</span>
                      )}
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
