'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Plus, Target, TrendingUp, AlertTriangle, FileText, BarChart3 } from 'lucide-react'
import toast from 'react-hot-toast'

interface SLODefinition {
  id: string
  name: string
  description: string
  metric_type: string
  threshold: number
  operator: string
  window: string
  alerting: boolean
  created_at: string
  updated_at: string
}

interface SLOMetrics {
  slo_id: string
  slo_name: string
  current_value: number
  target: number
  status: string
  window: string
  period_start: string
  period_end: string
}

interface SLOBudget {
  slo_id: string
  slo_name: string
  total_budget: number
  remaining_budget: number
  burned_budget: number
  burn_rate: number
  window: string
  period_start: string
  period_end: string
}

interface SLOAlert {
  id: string
  slo_id: string
  slo_name: string
  alert_type: string
  threshold: number
  current_value: number
  status: string
  created_at: string
}

interface SLOReport {
  id: string
  title: string
  period_start: string
  period_end: string
  total_slos: number
  met_slos: number
  missed_slos: number
  overall_compliance: number
  generated_at: string
}

export default function SLOAdvancedPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('definitions')
  const [isCreating, setIsCreating] = useState(false)
  const [editingSLO, setEditingSLO] = useState<SLODefinition | null>(null)
  const [newSLO, setNewSLO] = useState({
    name: '',
    description: '',
    metric_type: 'availability',
    threshold: 99.9,
    operator: 'gte',
    window: '30d',
    alerting: true
  })

  // 获取SLO定义
  const { data: sloDefinitions, isLoading: definitionsLoading, refetch: refetchDefinitions } = useQuery({
    queryKey: ['slo-definitions'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/definitions')
      return resp.data as SLODefinition[]
    }
  })

  // 获取SLO指标
  const { data: sloMetrics, isLoading: metricsLoading, refetch: refetchMetrics } = useQuery({
    queryKey: ['slo-metrics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/metrics')
      return resp.data as SLOMetrics[]
    }
  })

  // 获取SLO预算
  const { data: sloBudgets, isLoading: budgetsLoading, refetch: refetchBudgets } = useQuery({
    queryKey: ['slo-budgets'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/budgets')
      return resp.data as SLOBudget[]
    }
  })

  // 获取SLO告警
  const { data: sloAlerts, isLoading: alertsLoading, refetch: refetchAlerts } = useQuery({
    queryKey: ['slo-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/alerts')
      return resp.data as SLOAlert[]
    }
  })

  // 获取SLO报告
  const { data: sloReports, isLoading: reportsLoading, refetch: refetchReports } = useQuery({
    queryKey: ['slo-reports'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/reports')
      return resp.data as SLOReport[]
    }
  })

  // 创建SLO
  const createSLOMutation = useMutation({
    mutationFn: async (slo: any) => {
      const resp = await api.post('/api/v1/slo/definitions', slo)
      return resp.data
    },
    onSuccess: () => {
      toast.success('SLO创建成功')
      setIsCreating(false)
      setNewSLO({ name: '', description: '', metric_type: 'availability', threshold: 99.9, operator: 'gte', window: '30d', alerting: true })
      refetchDefinitions()
    },
    onError: (error: any) => {
      toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新SLO
  const updateSLOMutation = useMutation({
    mutationFn: async ({ sloId, data }: { sloId: string; data: any }) => {
      const resp = await api.patch(`/api/v1/slo/definitions/${sloId}`, data)
      return resp.data
    },
    onSuccess: () => {
      toast.success('SLO更新成功')
      setEditingSLO(null)
      refetchDefinitions()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 删除SLO
  const deleteSLOMutation = useMutation({
    mutationFn: async (sloId: string) => {
      const resp = await api.delete(`/api/v1/slo/definitions/${sloId}`)
      return resp.data
    },
    onSuccess: () => {
      toast.success('SLO删除成功')
      refetchDefinitions()
    },
    onError: (error: any) => {
      toast.error(`删除失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  const handleRefreshAll = () => {
    refetchDefinitions()
    refetchMetrics()
    refetchBudgets()
    refetchAlerts()
    refetchReports()
  }

  const handleCreateSLO = () => {
    createSLOMutation.mutate(newSLO)
  }

  const handleUpdateSLO = () => {
    if (!editingSLO) return
    updateSLOMutation.mutate({
      sloId: editingSLO.id,
      data: {
        name: editingSLO.name,
        description: editingSLO.description,
        metric_type: editingSLO.metric_type,
        threshold: editingSLO.threshold,
        operator: editingSLO.operator,
        window: editingSLO.window,
        alerting: editingSLO.alerting
      }
    })
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'met':
      case 'healthy':
      case 'on_track':
        return 'text-green-600 bg-green-50'
      case 'missed':
      case 'unhealthy':
      case 'at_risk':
        return 'text-red-600 bg-red-50'
      case 'warning':
      case 'degraded':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getMetricTypeIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'availability':
        return <Target className="h-4 w-4" />
      case 'latency':
        return <TrendingUp className="h-4 w-4" />
      case 'error_rate':
        return <AlertTriangle className="h-4 w-4" />
      case 'throughput':
        return <BarChart3 className="h-4 w-4" />
      default:
        return <Target className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级SLO管理</h1>
          <p className="text-sm text-gray-500 mt-1">服务级别目标定义、监控与报告</p>
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
          { id: 'definitions', label: 'SLO定义', icon: Target },
          { id: 'metrics', label: 'SLO指标', icon: TrendingUp },
          { id: 'budgets', label: '错误预算', icon: AlertTriangle },
          { id: 'alerts', label: 'SLO告警', icon: AlertTriangle },
          { id: 'reports', label: 'SLO报告', icon: FileText }
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

      {/* SLO定义 */}
      {activeTab === 'definitions' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>SLO定义列表</span>
                <Button onClick={() => setIsCreating(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  新建SLO
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {definitionsLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  {sloDefinitions?.map((slo) => (
                    <div key={slo.id} className="p-4 border rounded-lg">
                      {editingSLO?.id === slo.id ? (
                        <div className="space-y-3">
                          <Input
                            value={editingSLO.name}
                            onChange={(e) => setEditingSLO({ ...editingSLO, name: e.target.value })}
                          />
                          <Input
                            value={editingSLO.description}
                            onChange={(e) => setEditingSLO({ ...editingSLO, description: e.target.value })}
                          />
                          <Select
                            value={editingSLO.metric_type}
                            onChange={(e) => setEditingSLO({ ...editingSLO, metric_type: e.target.value })}
                            className="w-full"
                          >
                            <option value="availability">可用性</option>
                            <option value="latency">延迟</option>
                            <option value="error_rate">错误率</option>
                            <option value="throughput">吞吐量</option>
                          </Select>
                          <div className="grid grid-cols-2 gap-2">
                            <Input
                              type="number"
                              step="0.1"
                              value={editingSLO.threshold}
                              onChange={(e) => setEditingSLO({ ...editingSLO, threshold: parseFloat(e.target.value) })}
                            />
                            <Select
                              value={editingSLO.operator}
                              onChange={(e) => setEditingSLO({ ...editingSLO, operator: e.target.value })}
                            >
                              <option value="gte">≥</option>
                              <option value="lte">≤</option>
                              <option value="gt">&gt;</option>
                              <option value="lt">&lt;</option>
                            </Select>
                          </div>
                          <Select
                            value={editingSLO.window}
                            onChange={(e) => setEditingSLO({ ...editingSLO, window: e.target.value })}
                            className="w-full"
                          >
                            <option value="1h">1小时</option>
                            <option value="24h">24小时</option>
                            <option value="7d">7天</option>
                            <option value="30d">30天</option>
                            <option value="90d">90天</option>
                          </Select>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={editingSLO.alerting}
                              onCheckedChange={(checked) => setEditingSLO({ ...editingSLO, alerting: checked })}
                            />
                            <label className="text-sm">启用告警</label>
                          </div>
                          <div className="flex gap-2">
                            <Button onClick={handleUpdateSLO} size="sm">
                              保存
                            </Button>
                            <Button onClick={() => setEditingSLO(null)} variant="outline" size="sm">
                              取消
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {getMetricTypeIcon(slo.metric_type)}
                              <span className="font-medium">{slo.name}</span>
                              {slo.alerting && (
                                <span className="px-2 py-1 rounded text-xs bg-blue-50 text-blue-600">
                                  告警启用
                                </span>
                              )}
                            </div>
                            <div className="flex gap-2">
                              <Button onClick={() => setEditingSLO(slo)} variant="ghost" size="sm">
                                编辑
                              </Button>
                              <Button
                                onClick={() => deleteSLOMutation.mutate(slo.id)}
                                variant="ghost"
                                size="sm"
                              >
                                删除
                              </Button>
                            </div>
                          </div>
                          {slo.description && (
                            <p className="text-sm text-gray-600 mb-2">{slo.description}</p>
                          )}
                          <div className="text-sm text-gray-500">
                            <span>类型: {slo.metric_type}</span>
                            <span className="ml-4">目标: {slo.threshold}%</span>
                            <span className="ml-4">窗口: {slo.window}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建SLO表单 */}
          {isCreating && (
            <Card>
              <CardHeader>
                <CardTitle>创建SLO定义</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">SLO名称</label>
                    <Input
                      value={newSLO.name}
                      onChange={(e) => setNewSLO({ ...newSLO, name: e.target.value })}
                      placeholder="SLO名称"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">描述</label>
                    <Input
                      value={newSLO.description}
                      onChange={(e) => setNewSLO({ ...newSLO, description: e.target.value })}
                      placeholder="SLO描述"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">指标类型</label>
                    <Select
                      value={newSLO.metric_type}
                      onChange={(e) => setNewSLO({ ...newSLO, metric_type: e.target.value })}
                      className="w-full"
                    >
                      <option value="availability">可用性</option>
                      <option value="latency">延迟</option>
                      <option value="error_rate">错误率</option>
                      <option value="throughput">吞吐量</option>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">目标阈值 (%)</label>
                      <Input
                        type="number"
                        step="0.1"
                        value={newSLO.threshold}
                        onChange={(e) => setNewSLO({ ...newSLO, threshold: parseFloat(e.target.value) })}
                        min={0}
                        max={100}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">操作符</label>
                      <Select
                        value={newSLO.operator}
                        onChange={(e) => setNewSLO({ ...newSLO, operator: e.target.value })}
                        className="w-full"
                      >
                        <option value="gte">≥ (大于等于)</option>
                        <option value="lte">≤ (小于等于)</option>
                        <option value="gt">&gt; (大于)</option>
                        <option value="lt">&lt; (小于)</option>
                      </Select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">时间窗口</label>
                    <Select
                      value={newSLO.window}
                      onChange={(e) => setNewSLO({ ...newSLO, window: e.target.value })}
                      className="w-full"
                    >
                      <option value="1h">1小时</option>
                      <option value="24h">24小时</option>
                      <option value="7d">7天</option>
                      <option value="30d">30天</option>
                      <option value="90d">90天</option>
                    </Select>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={newSLO.alerting}
                      onCheckedChange={(checked) => setNewSLO({ ...newSLO, alerting: checked })}
                    />
                    <label className="text-sm">启用告警</label>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCreateSLO} disabled={createSLOMutation.isPending}>
                      {createSLOMutation.isPending ? '创建中...' : '创建'}
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

      {/* SLO指标 */}
      {activeTab === 'metrics' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              SLO指标监控
            </CardTitle>
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {sloMetrics?.map((metric) => (
                  <div key={metric.slo_id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{metric.slo_name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(metric.status)}`}>
                          {metric.status}
                        </span>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">{metric.current_value.toFixed(2)}%</div>
                        <div className="text-sm text-gray-500">目标: {metric.target}%</div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>窗口: {metric.window}</span>
                      <span className="ml-4">周期: {new Date(metric.period_start).toLocaleString()} - {new Date(metric.period_end).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 错误预算 */}
      {activeTab === 'budgets' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              错误预算
            </CardTitle>
          </CardHeader>
          <CardContent>
            {budgetsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {sloBudgets?.map((budget) => (
                  <div key={budget.slo_id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{budget.slo_name}</span>
                      <span className="text-sm text-gray-500">{budget.window}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mb-2">
                      <div>
                        <div className="text-sm text-gray-600">总预算</div>
                        <div className="text-lg font-bold">{budget.total_budget.toFixed(2)}%</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">剩余预算</div>
                        <div className="text-lg font-bold text-green-600">{budget.remaining_budget.toFixed(2)}%</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">已消耗</div>
                        <div className="text-lg font-bold text-red-600">{budget.burned_budget.toFixed(2)}%</div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      <span>消耗率: {budget.burn_rate.toFixed(2)}/h</span>
                      <span className="ml-4">周期: {new Date(budget.period_start).toLocaleString()} - {new Date(budget.period_end).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* SLO告警 */}
      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              SLO告警
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alertsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {sloAlerts?.map((alert) => (
                  <div key={alert.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{alert.slo_name}</span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(alert.status)}`}>
                          {alert.status}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {new Date(alert.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      <span>类型: {alert.alert_type}</span>
                      <span className="ml-4">阈值: {alert.threshold}%</span>
                      <span className="ml-4">当前: {alert.current_value.toFixed(2)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* SLO报告 */}
      {activeTab === 'reports' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              SLO报告
            </CardTitle>
          </CardHeader>
          <CardContent>
            {reportsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-3">
                {sloReports?.map((report) => (
                  <div key={report.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{report.title}</span>
                      <span className="text-sm text-gray-500">
                        {new Date(report.generated_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-4 gap-4 mb-2">
                      <div>
                        <div className="text-sm text-gray-600">总SLO数</div>
                        <div className="text-lg font-bold">{report.total_slos}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">达成</div>
                        <div className="text-lg font-bold text-green-600">{report.met_slos}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">未达成</div>
                        <div className="text-lg font-bold text-red-600">{report.missed_slos}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">整体合规率</div>
                        <div className="text-lg font-bold">{report.overall_compliance.toFixed(2)}%</div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      周期: {new Date(report.period_start).toLocaleString()} - {new Date(report.period_end).toLocaleString()}
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
