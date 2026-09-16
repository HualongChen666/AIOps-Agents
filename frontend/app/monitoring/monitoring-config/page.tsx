'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import api from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Settings, Database, Activity, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'

/**
 * 配置表单本地草稿 hook。
 *
 * 解决“每击键一次 PUT”与“输入被查询结果回填覆盖”的反模式：
 * - number/text 输入：onChange 只改本地草稿（setField），失焦(onBlur)时 flush 提交；
 * - switch/select 等离散项：改变即 commit 提交合并后的完整配置。
 */
function useDraft<T extends object>(
  remote: T | undefined,
  commitFn: (value: T) => void,
) {
  const [draft, setDraft] = useState<T | null>(null)

  useEffect(() => {
    if (remote) setDraft(remote)
  }, [remote])

  const setField = (patch: Partial<T>) =>
    setDraft((prev) => (prev ? { ...prev, ...patch } : prev))

  const flush = () => {
    if (draft) commitFn(draft)
  }

  const commit = (patch: Partial<T>) => {
    if (!draft) return
    const next = { ...draft, ...patch }
    setDraft(next)
    commitFn(next)
  }

  return { draft, setField, flush, commit }
}

interface MonitoringConfig {
  enabled: boolean
  data_retention_days: number
  sampling_rate: number
  enable_realtime: boolean
  enable_historical: boolean
  dashboard_refresh_interval: number
}

interface MetricsConfig {
  cpu_enabled: boolean
  memory_enabled: boolean
  disk_enabled: boolean
  network_enabled: boolean
  process_enabled: boolean
  collection_interval: number
  storage_backend: string
}

interface LoggingConfig {
  level: string
  format: string
  enable_file_logging: boolean
  enable_console_logging: boolean
  log_retention_days: number
  max_file_size_mb: number
  storage_backend: string
}

interface AlertThreshold {
  metric_name: string
  warning_threshold: number
  critical_threshold: number
  comparison: string
  enabled: boolean
}

interface AlertThresholdsConfig {
  thresholds: AlertThreshold[]
  notification_channels: string[]
  cooldown_seconds: number
}

interface MonitoringStatus {
  monitoring_enabled: boolean
  metrics_collection: {
    status: string
    last_collection: string
    collection_interval: number
  }
  logging: {
    status: string
    level: string
    storage_backend: string
  }
  alerting: {
    status: string
    active_thresholds: number
    total_thresholds: number
  }
  storage: {
    metrics_backend: string
    logs_backend: string
    traces_backend: string
  }
}

export default function MonitoringConfigPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('general')
  const [testBackend, setTestBackend] = useState('victoriametrics')
  // 通知通道以“原始文本”编辑，避免逗号/空格在每次回填时被过滤造成输入抖动。
  const [channelsText, setChannelsText] = useState('')

  // 获取监控配置
  const { data: monitoringConfig, isLoading: monitoringConfigLoading, refetch: refetchMonitoringConfig } = useQuery({
    queryKey: ['monitoring-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/config')
      return resp.data as MonitoringConfig
    }
  })

  // 获取指标配置
  const { data: metricsConfig, isLoading: metricsConfigLoading, refetch: refetchMetricsConfig } = useQuery({
    queryKey: ['metrics-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/metrics-config')
      return resp.data as MetricsConfig
    }
  })

  // 获取日志配置
  const { data: loggingConfig, isLoading: loggingConfigLoading, refetch: refetchLoggingConfig } = useQuery({
    queryKey: ['logging-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/logging-config')
      return resp.data as LoggingConfig
    }
  })

  // 获取告警阈值
  const { data: alertThresholds, isLoading: alertThresholdsLoading, refetch: refetchAlertThresholds } = useQuery({
    queryKey: ['alert-thresholds'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/alert-thresholds')
      return resp.data as AlertThresholdsConfig
    }
  })

  // 获取监控状态
  const { data: monitoringStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['monitoring-status'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/status')
      return resp.data as MonitoringStatus
    },
    refetchInterval: 30000
  })

  // 更新监控配置
  const updateMonitoringConfigMutation = useMutation({
    mutationFn: async (config: MonitoringConfig) => {
      const resp = await api.put('/api/v1/monitoring/config', config)
      return resp.data
    },
    onSuccess: () => {
      toast.success('监控配置更新成功')
      refetchMonitoringConfig()
      refetchStatus()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新指标配置
  const updateMetricsConfigMutation = useMutation({
    mutationFn: async (config: MetricsConfig) => {
      const resp = await api.put('/api/v1/monitoring/metrics-config', config)
      return resp.data
    },
    onSuccess: () => {
      toast.success('指标配置更新成功')
      refetchMetricsConfig()
      refetchStatus()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新日志配置
  const updateLoggingConfigMutation = useMutation({
    mutationFn: async (config: LoggingConfig) => {
      const resp = await api.put('/api/v1/monitoring/logging-config', config)
      return resp.data
    },
    onSuccess: () => {
      toast.success('日志配置更新成功')
      refetchLoggingConfig()
      refetchStatus()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 更新告警阈值
  const updateAlertThresholdsMutation = useMutation({
    mutationFn: async (config: AlertThresholdsConfig) => {
      const resp = await api.put('/api/v1/monitoring/alert-thresholds', config)
      return resp.data
    },
    onSuccess: () => {
      toast.success('告警阈值更新成功')
      refetchAlertThresholds()
      refetchStatus()
    },
    onError: (error: any) => {
      toast.error(`更新失败: ${error.response?.data?.detail || error.message}`)
    }
  })

  // 测试连接
  const { data: testResult, isLoading: testLoading, refetch: refetchTest } = useQuery({
    queryKey: ['test-connection', testBackend],
    queryFn: async () => {
      const resp = await api.post('/api/v1/monitoring/test-connection', null, {
        params: { backend: testBackend }
      })
      return resp.data
    },
    enabled: false
  })

  // 各配置表单的本地草稿（失焦提交，避免每击键写库）
  const monitoringForm = useDraft<MonitoringConfig>(monitoringConfig, (v) =>
    updateMonitoringConfigMutation.mutate(v)
  )
  const metricsForm = useDraft<MetricsConfig>(metricsConfig, (v) =>
    updateMetricsConfigMutation.mutate(v)
  )
  const loggingForm = useDraft<LoggingConfig>(loggingConfig, (v) =>
    updateLoggingConfigMutation.mutate(v)
  )
  const thresholdsForm = useDraft<AlertThresholdsConfig>(alertThresholds, (v) =>
    updateAlertThresholdsMutation.mutate(v)
  )

  useEffect(() => {
    if (alertThresholds) {
      setChannelsText((alertThresholds.notification_channels || []).join(', '))
    }
  }, [alertThresholds])

  const handleRefreshAll = () => {
    refetchMonitoringConfig()
    refetchMetricsConfig()
    refetchLoggingConfig()
    refetchAlertThresholds()
    refetchStatus()
  }
  const handleTestConnection = () => {
    refetchTest()
  }

  const getStatusIcon = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'running':
      case 'active':
      case 'connected':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'stopped':
      case 'inactive':
      case 'disconnected':
        return <XCircle className="h-4 w-4 text-red-600" />
      default:
        return <Activity className="h-4 w-4 text-gray-600" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">监控配置</h1>
          <p className="text-sm text-gray-500 mt-1">监控指标、日志和告警配置管理</p>
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
          { id: 'general', label: '通用配置', icon: Settings },
          { id: 'metrics', label: '指标配置', icon: Activity },
          { id: 'logging', label: '日志配置', icon: Database },
          { id: 'alerts', label: '告警配置', icon: AlertTriangle },
          { id: 'status', label: '监控状态', icon: CheckCircle }
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

      {/* 通用配置 */}
      {activeTab === 'general' && (
        <Card>
          <CardHeader>
            <CardTitle>通用监控配置</CardTitle>
          </CardHeader>
          <CardContent>
            {monitoringConfigLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">启用监控</label>
                  <Switch
                    checked={monitoringForm.draft?.enabled || false}
                    onCheckedChange={(checked) =>
                      monitoringForm.commit({ enabled: checked })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">数据保留天数</label>
                  <Input
                    type="number"
                    value={monitoringForm.draft?.data_retention_days ?? 30}
                    onChange={(e) =>
                      monitoringForm.setField({ data_retention_days: parseInt(e.target.value) || 0 })
                    }
                    onBlur={monitoringForm.flush}
                    min={1}
                    max={365}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">采样率</label>
                  <Input
                    type="number"
                    step="0.1"
                    value={monitoringForm.draft?.sampling_rate ?? 1.0}
                    onChange={(e) =>
                      monitoringForm.setField({ sampling_rate: parseFloat(e.target.value) || 0 })
                    }
                    onBlur={monitoringForm.flush}
                    min={0.1}
                    max={1.0}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">启用实时监控</label>
                  <Switch
                    checked={monitoringForm.draft?.enable_realtime || false}
                    onCheckedChange={(checked) =>
                      monitoringForm.commit({ enable_realtime: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">启用历史数据</label>
                  <Switch
                    checked={monitoringForm.draft?.enable_historical || false}
                    onCheckedChange={(checked) =>
                      monitoringForm.commit({ enable_historical: checked })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">仪表板刷新间隔（秒）</label>
                  <Input
                    type="number"
                    value={monitoringForm.draft?.dashboard_refresh_interval ?? 30}
                    onChange={(e) =>
                      monitoringForm.setField({ dashboard_refresh_interval: parseInt(e.target.value) || 0 })
                    }
                    onBlur={monitoringForm.flush}
                    min={5}
                    max={300}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 指标配置 */}
      {activeTab === 'metrics' && (
        <Card>
          <CardHeader>
            <CardTitle>指标收集配置</CardTitle>
          </CardHeader>
          <CardContent>
            {metricsConfigLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">CPU指标收集</label>
                  <Switch
                    checked={metricsForm.draft?.cpu_enabled || false}
                    onCheckedChange={(checked) =>
                      metricsForm.commit({ cpu_enabled: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">内存指标收集</label>
                  <Switch
                    checked={metricsForm.draft?.memory_enabled || false}
                    onCheckedChange={(checked) =>
                      metricsForm.commit({ memory_enabled: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">磁盘指标收集</label>
                  <Switch
                    checked={metricsForm.draft?.disk_enabled || false}
                    onCheckedChange={(checked) =>
                      metricsForm.commit({ disk_enabled: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">网络指标收集</label>
                  <Switch
                    checked={metricsForm.draft?.network_enabled || false}
                    onCheckedChange={(checked) =>
                      metricsForm.commit({ network_enabled: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">进程指标收集</label>
                  <Switch
                    checked={metricsForm.draft?.process_enabled || false}
                    onCheckedChange={(checked) =>
                      metricsForm.commit({ process_enabled: checked })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">收集间隔（秒）</label>
                  <Input
                    type="number"
                    value={metricsForm.draft?.collection_interval ?? 60}
                    onChange={(e) =>
                      metricsForm.setField({ collection_interval: parseInt(e.target.value) || 0 })
                    }
                    onBlur={metricsForm.flush}
                    min={10}
                    max={3600}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">存储后端</label>
                  <select
                    value={metricsForm.draft?.storage_backend || 'victoriametrics'}
                    onChange={(e) =>
                      metricsForm.commit({ storage_backend: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="victoriametrics">VictoriaMetrics</option>
                    <option value="prometheus">Prometheus</option>
                    <option value="influxdb">InfluxDB</option>
                  </select>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 日志配置 */}
      {activeTab === 'logging' && (
        <Card>
          <CardHeader>
            <CardTitle>日志配置</CardTitle>
          </CardHeader>
          <CardContent>
            {loggingConfigLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">日志级别</label>
                  <select
                    value={loggingForm.draft?.level || 'INFO'}
                    onChange={(e) =>
                      loggingForm.commit({ level: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">日志格式</label>
                  <select
                    value={loggingForm.draft?.format || 'json'}
                    onChange={(e) =>
                      loggingForm.commit({ format: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="json">JSON</option>
                    <option value="text">Text</option>
                  </select>
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">启用文件日志</label>
                  <Switch
                    checked={loggingForm.draft?.enable_file_logging || false}
                    onCheckedChange={(checked) =>
                      loggingForm.commit({ enable_file_logging: checked })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">启用控制台日志</label>
                  <Switch
                    checked={loggingForm.draft?.enable_console_logging || false}
                    onCheckedChange={(checked) =>
                      loggingForm.commit({ enable_console_logging: checked })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">日志保留天数</label>
                  <Input
                    type="number"
                    value={loggingForm.draft?.log_retention_days ?? 7}
                    onChange={(e) =>
                      loggingForm.setField({ log_retention_days: parseInt(e.target.value) || 0 })
                    }
                    onBlur={loggingForm.flush}
                    min={1}
                    max={365}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">最大文件大小（MB）</label>
                  <Input
                    type="number"
                    value={loggingForm.draft?.max_file_size_mb ?? 100}
                    onChange={(e) =>
                      loggingForm.setField({ max_file_size_mb: parseInt(e.target.value) || 0 })
                    }
                    onBlur={loggingForm.flush}
                    min={1}
                    max={1000}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">日志存储后端</label>
                  <select
                    value={loggingForm.draft?.storage_backend || 'loki'}
                    onChange={(e) =>
                      loggingForm.commit({ storage_backend: e.target.value })
                    }
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="loki">Loki</option>
                    <option value="elasticsearch">Elasticsearch</option>
                    <option value="file">File</option>
                  </select>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 告警配置 */}
      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle>告警阈值配置</CardTitle>
          </CardHeader>
          <CardContent>
            {alertThresholdsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium mb-2">告警阈值</h3>
                  <div className="space-y-3">
                    {thresholdsForm.draft?.thresholds?.map((threshold, index) => (
                      <div key={index} className="p-4 border rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{threshold.metric_name}</span>
                          <Switch
                            checked={threshold.enabled}
                            onCheckedChange={(checked) => {
                              const newThresholds = [...(thresholdsForm.draft?.thresholds || [])]
                              newThresholds[index] = { ...newThresholds[index], enabled: checked }
                              thresholdsForm.commit({ thresholds: newThresholds })
                            }}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs text-gray-600 mb-1">警告阈值</label>
                            <Input
                              type="number"
                              value={threshold.warning_threshold}
                              onChange={(e) => {
                                const newThresholds = [...(thresholdsForm.draft?.thresholds || [])]
                                newThresholds[index] = {
                                  ...newThresholds[index],
                                  warning_threshold: parseFloat(e.target.value) || 0
                                }
                                thresholdsForm.setField({ thresholds: newThresholds })
                              }}
                              onBlur={thresholdsForm.flush}
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-600 mb-1">严重阈值</label>
                            <Input
                              type="number"
                              value={threshold.critical_threshold}
                              onChange={(e) => {
                                const newThresholds = [...(thresholdsForm.draft?.thresholds || [])]
                                newThresholds[index] = {
                                  ...newThresholds[index],
                                  critical_threshold: parseFloat(e.target.value) || 0
                                }
                                thresholdsForm.setField({ thresholds: newThresholds })
                              }}
                              onBlur={thresholdsForm.flush}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">通知通道</label>
                  <Input
                    value={channelsText}
                    onChange={(e) => setChannelsText(e.target.value)}
                    onBlur={() =>
                      thresholdsForm.commit({
                        notification_channels: channelsText
                          .split(',')
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                    placeholder="email, slack, webhook"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">冷却时间（秒）</label>
                  <Input
                    type="number"
                    value={thresholdsForm.draft?.cooldown_seconds ?? 300}
                    onChange={(e) =>
                      thresholdsForm.setField({ cooldown_seconds: parseInt(e.target.value) || 0 })
                    }
                    onBlur={thresholdsForm.flush}
                    min={0}
                    max={3600}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 监控状态 */}
      {activeTab === 'status' && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>监控状态概览</CardTitle>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">监控启用状态</span>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(monitoringStatus?.monitoring_enabled ? 'active' : 'inactive')}
                      <span className="text-sm">
                        {monitoringStatus?.monitoring_enabled ? '已启用' : '已禁用'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">指标收集</span>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(monitoringStatus?.metrics_collection?.status)}
                      <span className="text-sm">{monitoringStatus?.metrics_collection?.status}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">日志记录</span>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(monitoringStatus?.logging?.status)}
                      <span className="text-sm">{monitoringStatus?.logging?.status}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">告警系统</span>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(monitoringStatus?.alerting?.status)}
                      <span className="text-sm">{monitoringStatus?.alerting?.status}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>存储后端状态</CardTitle>
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">指标存储</span>
                    <span className="text-sm">{monitoringStatus?.storage?.metrics_backend}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">日志存储</span>
                    <span className="text-sm">{monitoringStatus?.storage?.logs_backend}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium">追踪存储</span>
                    <span className="text-sm">{monitoringStatus?.storage?.traces_backend}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>连接测试</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex gap-2">
                  <select
                    value={testBackend}
                    onChange={(e) => setTestBackend(e.target.value)}
                    className="px-3 py-2 border rounded-md"
                  >
                    <option value="victoriametrics">VictoriaMetrics</option>
                    <option value="loki">Loki</option>
                    <option value="tempo">Tempo</option>
                  </select>
                  <Button onClick={handleTestConnection} disabled={testLoading}>
                    {testLoading ? '测试中...' : '测试连接'}
                  </Button>
                </div>
                {testResult && (
                  <div className="p-4 bg-gray-50 rounded">
                    <div className="flex items-center gap-2 mb-2">
                      {getStatusIcon(testResult.status)}
                      <span className="font-medium">{testResult.status}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      <div>后端: {testResult.backend}</div>
                      <div>延迟: {testResult.latency_ms}ms</div>
                      <div>版本: {testResult.version}</div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
