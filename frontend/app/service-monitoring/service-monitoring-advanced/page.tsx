'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Plus, Edit, Trash2, Activity, AlertTriangle, LayoutDashboard, Bell } from 'lucide-react'
import toast from 'react-hot-toast'

interface MonitoredService {
  id: string
  name: string
  status: string
  health_score: number
  last_check: string
  endpoint: string
  tags: string[]
}

interface ServiceAlert {
  id: string
  name: string
  service_name: string
  metric_name: string
  condition: string
  threshold: number
  severity: string
  description: string | null
  enabled: boolean
  notification_channels: string[]
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

interface ServiceDashboard {
  id: string
  name: string
  description: string | null
  widgets: Record<string, any>[]
  refresh_interval_seconds: number
  is_public: boolean
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export default function ServiceMonitoringAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('services')
  const [isCreatingAlert, setIsCreatingAlert] = useState(false)
  const [isCreatingDashboard, setIsCreatingDashboard] = useState(false)
  const [editingAlert, setEditingAlert] = useState<ServiceAlert | null>(null)
  const [newAlert, setNewAlert] = useState({
    name: '',
    service_name: '',
    metric_name: '',
    condition: 'greater_than',
    threshold: 0,
    severity: 'warning',
    description: '',
    notification_channels: []
  })
  const [newDashboard, setNewDashboard] = useState({
    name: '',
    description: '',
    widgets: '[]',
    refresh_interval_seconds: 30,
    is_public: false
  })

  // 获取监控服务列表
  const { data: services, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
    queryKey: ['service-monitoring-services'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/service-monitoring/services')
      return resp.data as MonitoredService[]
    }
  })

  // 获取告警列表
  const { data: alerts, isLoading: alertsLoading, refetch: refetchAlerts } = useQuery({
    queryKey: ['service-monitoring-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/service-monitoring/alerts')
      return resp.data as ServiceAlert[]
    }
  })

  // 获取仪表板列表
  const { data: dashboards, isLoading: dashboardsLoading, refetch: refetchDashboards } = useQuery({
    queryKey: ['service-monitoring-dashboards'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/service-monitoring/dashboards')
      return resp.data as ServiceDashboard[]
    }
  })

  // 创建告警
  const createAlertMutation = useMutation({
    mutationFn: async (alert: any) => {
      const resp = await api.post('/api/v1/service-monitoring/alerts', alert)
      return resp.data
    },
    onSuccess: () => {
      toast.success('告警创建成功')
      setIsCreatingAlert(false)
      setNewAlert({ name: '', service_name: '', metric_name: '', condition: 'greater_than', threshold: 0, severity: 'warning', description: '', notification_channels: [] })
      refetchAlerts()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新告警
  const updateAlertMutation = useMutation({
    mutationFn: async ({ alertId, data }: { alertId: string; data: any }) => {
      const resp = await api.put(`/api/v1/service-monitoring/alerts/${alertId}`, data)
      return resp.data
    },
    onSuccess: () => {
      toast.success('告警更新成功')
      setEditingAlert(null)
      refetchAlerts()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除告警
  const deleteAlertMutation = useMutation({
    mutationFn: async (alertId: string) => {
      const resp = await api.delete(`/api/v1/service-monitoring/alerts/${alertId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('告警删除成功')
      refetchAlerts()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 创建仪表板
  const createDashboardMutation = useMutation({
    mutationFn: async (dashboard: any) => {
      const resp = await api.post('/api/v1/service-monitoring/dashboards', dashboard)
      return resp.data
    },
    onSuccess: () => {
      toast.success('仪表板创建成功')
      setIsCreatingDashboard(false)
      setNewDashboard({ name: '', description: '', widgets: '[]', refresh_interval_seconds: 30, is_public: false })
      refetchDashboards()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除仪表板
  const deleteDashboardMutation = useMutation({
    mutationFn: async (dashboardId: string) => {
      const resp = await api.delete(`/api/v1/service-monitoring/dashboards/${dashboardId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('仪表板删除成功')
      refetchDashboards()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchServices()
    refetchAlerts()
    refetchDashboards()
  }

  const handleCreateAlert = () => {
    createAlertMutation.mutate(newAlert)
  }

  const handleUpdateAlert = () => {
    if (!editingAlert) return
    updateAlertMutation.mutate({
      alertId: editingAlert.id,
      data: {
        name: editingAlert.name,
        service_name: editingAlert.service_name,
        metric_name: editingAlert.metric_name,
        condition: editingAlert.condition,
        threshold: editingAlert.threshold,
        severity: editingAlert.severity,
        description: editingAlert.description,
        enabled: editingAlert.enabled,
        notification_channels: editingAlert.notification_channels
      }
    })
  }

  const handleCreateDashboard = () => {
    try {
      const widgets = JSON.parse(newDashboard.widgets)
      createDashboardMutation.mutate({
        name: newDashboard.name,
        description: newDashboard.description,
        widgets,
        refresh_interval_seconds: newDashboard.refresh_interval_seconds,
        is_public: newDashboard.is_public
      })
    } catch (e) {
      toast.error('Widgets JSON格式错误')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'up':
        return 'text-green-600 bg-green-50'
      case 'unhealthy':
      case 'down':
        return 'text-red-600 bg-red-50'
      case 'degraded':
      case 'warning':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'text-red-600 bg-red-50'
      case 'error':
        return 'text-red-500 bg-red-50'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50'
      case 'info':
        return 'text-blue-600 bg-blue-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级服务监控</h1>
          <p className="text-sm text-gray-500 mt-1">服务健康监控、告警管理与仪表板</p>
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
          { id: 'services', label: '服务列表', icon: Activity },
          { id: 'alerts', label: '告警管理', icon: Bell },
          { id: 'dashboards', label: '仪表板', icon: LayoutDashboard }
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

      {/* 服务列表 */}
      {activeTab === 'services' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              监控服务列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {servicesLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {services?.map((service) => (
                  <div key={service.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{service.name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(service.status)}`}>
                          {service.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">健康分: {service.health_score.toFixed(1)}</span>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>端点: {service.endpoint}</span>
                      <span className="ml-4">最后检查: {new Date(service.last_check).toLocaleString()}</span>
                    </div>
                    {service.tags && service.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {service.tags.map((tag, index) => (
                          <span key={index} className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 告警管理 */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>告警规则列表</span>
                <Button onClick={() => setIsCreatingAlert(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  新建告警
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {alertsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {alerts?.map((alert) => (
                    <div key={alert.id} className="p-4 border rounded-lg">
                      {editingAlert?.id === alert.id ? (
                        <div className="space-y-3">
                          <Input
                            value={editingAlert.name}
                            onChange={(e) => setEditingAlert({ ...editingAlert, name: e.target.value })}
                          />
                          <Input
                            value={editingAlert.service_name}
                            onChange={(e) => setEditingAlert({ ...editingAlert, service_name: e.target.value })}
                            placeholder="服务名称"
                          />
                          <Input
                            value={editingAlert.metric_name}
                            onChange={(e) => setEditingAlert({ ...editingAlert, metric_name: e.target.value })}
                            placeholder="指标名称"
                          />
                          <div className="grid grid-cols-2 gap-2">
                            <Select
                              value={editingAlert.condition}
                              onChange={(e) => setEditingAlert({ ...editingAlert, condition: e.target.value })}
                            >
                              <option value="greater_than">大于</option>
                              <option value="less_than">小于</option>
                              <option value="equals">等于</option>
                            </Select>
                            <Input
                              type="number"
                              value={editingAlert.threshold}
                              onChange={(e) => setEditingAlert({ ...editingAlert, threshold: parseFloat(e.target.value) })}
                            />
                          </div>
                          <Select
                            value={editingAlert.severity}
                            onChange={(e) => setEditingAlert({ ...editingAlert, severity: e.target.value })}
                          >
                            <option value="info">Info</option>
                            <option value="warning">Warning</option>
                            <option value="error">Error</option>
                            <option value="critical">Critical</option>
                          </Select>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={editingAlert.enabled}
                              onCheckedChange={(checked) => setEditingAlert({ ...editingAlert, enabled: checked })}
                            />
                            <label className="text-sm">启用</label>
                          </div>
                          <div className="flex gap-2">
                            <Button onClick={handleUpdateAlert} size="sm">
                              保存
                            </Button>
                            <Button onClick={() => setEditingAlert(null)} variant="outline" size="sm">
                              取消
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{alert.name}</span>
                              <span className={`px-2 py-1 rounded text-xs ${getSeverityColor(alert.severity)}`}>
                                {alert.severity}
                              </span>
                              <span className={`px-2 py-1 rounded text-xs ${alert.enabled ? 'text-green-600 bg-green-50' : 'text-gray-600 bg-gray-50'}`}>
                                {alert.enabled ? '启用' : '禁用'}
                              </span>
                            </div>
                            <div className="flex gap-2">
                              <Button onClick={() => setEditingAlert(alert)} variant="ghost" size="sm">
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                onClick={() => deleteAlertMutation.mutate(alert.id)}
                                variant="ghost"
                                size="sm"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                          <div className="text-sm text-gray-500">
                            <span>服务: {alert.service_name}</span>
                            <span className="ml-4">指标: {alert.metric_name}</span>
                            <span className="ml-4">
                              {alert.condition} {alert.threshold}
                            </span>
                          </div>
                          {alert.description && (
                            <p className="text-sm text-gray-600 mt-1">{alert.description}</p>
                          )}
                          {alert.notification_channels && alert.notification_channels.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {alert.notification_channels.map((channel, index) => (
                                <span key={index} className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs">
                                  {channel}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建告警表单 */}
          {isCreatingAlert && (
            <Card>
              <CardHeader>
                <CardTitle>创建告警规则</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">告警名称</label>
                    <Input
                      value={newAlert.name}
                      onChange={(e) => setNewAlert({ ...newAlert, name: e.target.value })}
                      placeholder="告警名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">服务名称</label>
                    <Input
                      value={newAlert.service_name}
                      onChange={(e) => setNewAlert({ ...newAlert, service_name: e.target.value })}
                      placeholder="service-name"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">指标名称</label>
                    <Input
                      value={newAlert.metric_name}
                      onChange={(e) => setNewAlert({ ...newAlert, metric_name: e.target.value })}
                      placeholder="cpu_usage"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">条件</label>
                      <Select
                        value={newAlert.condition}
                        onChange={(e) => setNewAlert({ ...newAlert, condition: e.target.value })}
                        className="w-full"
                      >
                        <option value="greater_than">大于</option>
                        <option value="less_than">小于</option>
                        <option value="equals">等于</option>
                      </Select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">阈值</label>
                      <Input
                        type="number"
                        value={newAlert.threshold}
                        onChange={(e) => setNewAlert({ ...newAlert, threshold: parseFloat(e.target.value) })}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">严重级别</label>
                    <Select
                      value={newAlert.severity}
                      onChange={(e) => setNewAlert({ ...newAlert, severity: e.target.value })}
                      className="w-full"
                    >
                      <option value="info">Info</option>
                      <option value="warning">Warning</option>
                      <option value="error">Error</option>
                      <option value="critical">Critical</option>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={newAlert.description}
                      onChange={(e) => setNewAlert({ ...newAlert, description: e.target.value })}
                      placeholder="告警描述"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateAlert} disabled={createAlertMutation.isPending}>
                      {createAlertMutation.isPending ? '创建中...' : '创建'}
                    </Button>
                    <Button onClick={() => setIsCreatingAlert(false)} variant="outline">
                      取消
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 仪表板 */}
      {activeTab === 'dashboards' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>仪表板列表</span>
                <Button onClick={() => setIsCreatingDashboard(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  新建仪表板
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboardsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {dashboards?.map((dashboard) => (
                    <div key={dashboard.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{dashboard.name}</span>
                          {dashboard.is_public && (
                            <span className="px-2 py-1 rounded text-xs bg-blue-50 text-blue-600">
                              公开
                            </span>
                          )}
                        </div>
                        <Button
                          onClick={() => deleteDashboardMutation.mutate(dashboard.id)}
                          variant="ghost"
                          size="sm"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      {dashboard.description && (
                        <p className="text-sm text-gray-600 mb-2">{dashboard.description}</p>
                      )}
                      <div className="text-sm text-gray-500">
                        <span>组件数: {dashboard.widgets.length}</span>
                        <span className="ml-4">刷新间隔: {dashboard.refresh_interval_seconds}s</span>
                        <span className="ml-4">更新: {new Date(dashboard.updated_at).toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建仪表板表单 */}
          {isCreatingDashboard && (
            <Card>
              <CardHeader>
                <CardTitle>创建仪表板</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">仪表板名称</label>
                    <Input
                      value={newDashboard.name}
                      onChange={(e) => setNewDashboard({ ...newDashboard, name: e.target.value })}
                      placeholder="仪表板名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={newDashboard.description}
                      onChange={(e) => setNewDashboard({ ...newDashboard, description: e.target.value })}
                      placeholder="仪表板描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">组件配置（JSON）</label>
                    <textarea
                      value={newDashboard.widgets}
                      onChange={(e) => setNewDashboard({ ...newDashboard, widgets: e.target.value })}
                      className="w-full px-3 py-2 border rounded-md"
                      rows={4}
                      placeholder='[{"type": "metric", "title": "CPU", "query": "cpu_usage"}]'
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">刷新间隔（秒）</label>
                    <Input
                      type="number"
                      value={newDashboard.refresh_interval_seconds}
                      onChange={(e) => setNewDashboard({ ...newDashboard, refresh_interval_seconds: parseInt(e.target.value) })}
                      min={5}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={newDashboard.is_public}
                      onCheckedChange={(checked) => setNewDashboard({ ...newDashboard, is_public: checked })}
                    />
                    <label className="text-sm">公开仪表板</label>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateDashboard} disabled={createDashboardMutation.isPending}>
                      {createDashboardMutation.isPending ? '创建中...' : '创建'}
                    </Button>
                    <Button onClick={() => setIsCreatingDashboard(false)} variant="outline">
                      取消
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
