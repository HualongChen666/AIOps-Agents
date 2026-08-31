'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Activity, Database, Search, GitBranch, Server, AlertCircle, TrendingUp } from 'lucide-react'

interface LogAlertRule {
  id: string
  name: string
  pattern: string
  severity: string
  status: string
  triggered_count: number
  last_triggered: string
  notification_channels: string[]
}

interface LogAlertingResponse {
  total_rules: number
  active_rules: number
  inactive_rules: number
  total_alerts: number
  rules: LogAlertRule[]
}

interface LogPattern {
  pattern: string
  count: number
  frequency: number
  first_seen: string
  last_seen: string
  severity: string
}

interface LogAnalysisResponse {
  total_logs_analyzed: number
  unique_patterns: number
  error_patterns: number
  warning_patterns: number
  time_range: string
  patterns: LogPattern[]
}

interface ElasticsearchLog {
  _id: string
  _index: string
  _source: {
    timestamp: string
    level: string
    service: string
    message: string
  }
}

interface ElasticsearchResponse {
  es_url: string
  es_version: string
  cluster_name: string
  nodes_count: number
  total_indices: number
  total_documents: number
  data_size_gb: number
  query: string
  time_range: string
  logs: ElasticsearchLog[]
}

interface TempoTrace {
  trace_id: string
  service: string
  start_time: string
  duration_ms: number
  span_count: number
  root_span: string
}

interface TempoResponse {
  tempo_url: string
  tempo_version: string
  total_traces: number
  search_duration_ms: number
  service: string
  trace_id: string
  time_range: string
  traces: TempoTrace[]
}

interface LokiLog {
  stream: Record<string, string>
  values: [string, string][]
}

interface LokiResponse {
  loki_url: string
  loki_version: string
  total_streams: number
  ingestion_rate_mb: number
  query: string
  time_range: string
  logs: LokiLog[]
}

interface VictoriaMetric {
  metric: Record<string, string>
  values: [string, string][]
}

interface VictoriaMetricsResponse {
  vm_url: string
  vm_version: string
  total_series: number
  data_size_gb: number
  query: string
  time_range: string
  metrics: VictoriaMetric[]
}

export default function MonitoringAdvancedPage() {
  const [activeTab, setActiveTab] = useState('log-alerting')
  const [alertStatus, setAlertStatus] = useState('all')
  const [logSeverity, setLogSeverity] = useState('all')
  const [timeRange, setTimeRange] = useState('24h')
  const [esQuery, setEsQuery] = useState('*')
  const [tempoService, setTempoService] = useState('')
  const [lokiQuery, setLokiQuery] = useState('{job="varlogs"}')
  const [vmQuery, setVmQuery] = useState('up')

  // 获取日志告警数据
  const { data: logAlertingData, isLoading: logAlertingLoading, error: logAlertingError, refetch: refetchLogAlerting } = useQuery({
    queryKey: ['monitoring-log-alerting', alertStatus],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/log-alerting', {
        params: { status: alertStatus }
      })
      return resp.data as LogAlertingResponse
    },
    refetchInterval: 60000
  })

  // 获取日志分析数据
  const { data: logAnalysisData, isLoading: logAnalysisLoading, error: logAnalysisError, refetch: refetchLogAnalysis } = useQuery({
    queryKey: ['monitoring-log-analysis', logSeverity, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/log-analysis', {
        params: { severity: logSeverity, time_range: timeRange }
      })
      return resp.data as LogAnalysisResponse
    },
    refetchInterval: 60000
  })

  // 获取Elasticsearch日志
  const { data: esData, isLoading: esLoading, error: esError, refetch: refetchES } = useQuery({
    queryKey: ['monitoring-elasticsearch', esQuery, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/elasticsearch', {
        params: { query: esQuery, time_range: timeRange }
      })
      return resp.data as ElasticsearchResponse
    },
    refetchInterval: 60000,
    enabled: activeTab === 'elasticsearch'
  })

  // 获取Tempo追踪
  const { data: tempoData, isLoading: tempoLoading, error: tempoError, refetch: refetchTempo } = useQuery({
    queryKey: ['monitoring-tempo', tempoService, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/tempo', {
        params: { service: tempoService, time_range: timeRange }
      })
      return resp.data as TempoResponse
    },
    refetchInterval: 60000,
    enabled: activeTab === 'tempo'
  })

  // 获取Loki日志
  const { data: lokiData, isLoading: lokiLoading, error: lokiError, refetch: refetchLoki } = useQuery({
    queryKey: ['monitoring-loki', lokiQuery, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/loki', {
        params: { query: lokiQuery, time_range: timeRange }
      })
      return resp.data as LokiResponse
    },
    refetchInterval: 60000,
    enabled: activeTab === 'loki'
  })

  // 获取VictoriaMetrics
  const { data: vmData, isLoading: vmLoading, error: vmError, refetch: refetchVM } = useQuery({
    queryKey: ['monitoring-victoriametrics', vmQuery, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/victoriametrics', {
        params: { query: vmQuery, time_range: timeRange }
      })
      return resp.data as VictoriaMetricsResponse
    },
    refetchInterval: 60000,
    enabled: activeTab === 'victoriametrics'
  })

  const handleRefreshAll = () => {
    refetchLogAlerting()
    refetchLogAnalysis()
    refetchES()
    refetchTempo()
    refetchLoki()
    refetchVM()
  }

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
      case 'error':
        return 'text-red-600 bg-red-50'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50'
      case 'info':
        return 'text-blue-600 bg-blue-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'text-green-600 bg-green-50'
      case 'inactive':
        return 'text-gray-600 bg-gray-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级监控</h1>
          <p className="text-sm text-gray-500 mt-1">多源日志、追踪与指标集成监控</p>
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
          { id: 'log-alerting', label: '日志告警', icon: AlertCircle },
          { id: 'log-analysis', label: '日志分析', icon: Search },
          { id: 'elasticsearch', label: 'Elasticsearch', icon: Database },
          { id: 'tempo', label: 'Tempo追踪', icon: GitBranch },
          { id: 'loki', label: 'Loki日志', icon: Server },
          { id: 'victoriametrics', label: 'VictoriaMetrics', icon: Activity }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors whitespace-nowrap ${
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

      {/* 控制面板 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">查询参数</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">时间范围</label>
              <Select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="w-full"
              >
                <option value="5m">5分钟</option>
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
              </Select>
            </div>
            {activeTab === 'log-alerting' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">规则状态</label>
                <Select
                  value={alertStatus}
                  onChange={(e) => setAlertStatus(e.target.value)}
                  className="w-full"
                >
                  <option value="all">全部</option>
                  <option value="active">活跃</option>
                  <option value="inactive">非活跃</option>
                </Select>
              </div>
            )}
            {activeTab === 'log-analysis' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">日志级别</label>
                <Select
                  value={logSeverity}
                  onChange={(e) => setLogSeverity(e.target.value)}
                  className="w-full"
                >
                  <option value="all">全部</option>
                  <option value="error">错误</option>
                  <option value="warning">警告</option>
                  <option value="info">信息</option>
                </Select>
              </div>
            )}
            {activeTab === 'elasticsearch' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">查询语句</label>
                <input
                  type="text"
                  value={esQuery}
                  onChange={(e) => setEsQuery(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="*"
                />
              </div>
            )}
            {activeTab === 'tempo' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">服务名称</label>
                <input
                  type="text"
                  value={tempoService}
                  onChange={(e) => setTempoService(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="service-name"
                />
              </div>
            )}
            {activeTab === 'loki' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">LogQL查询</label>
                <input
                  type="text"
                  value={lokiQuery}
                  onChange={(e) => setLokiQuery(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder='{job="varlogs"}'
                />
              </div>
            )}
            {activeTab === 'victoriametrics' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">MetricsQL查询</label>
                <input
                  type="text"
                  value={vmQuery}
                  onChange={(e) => setVmQuery(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="up"
                />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 日志告警 */}
      {activeTab === 'log-alerting' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">总规则数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{logAlertingData?.total_rules || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">活跃规则</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">{logAlertingData?.active_rules || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">非活跃规则</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-600">{logAlertingData?.inactive_rules || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">总告警数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{logAlertingData?.total_alerts || 0}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>告警规则列表</CardTitle>
            </CardHeader>
            <CardContent>
              {logAlertingLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : logAlertingError ? (
                <div className="text-center text-red-500 py-8">加载失败</div>
              ) : (
                <div className="space-y-3">
                  {logAlertingData?.rules?.map((rule) => (
                    <div key={rule.id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium">{rule.name}</h3>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(rule.status)}`}>
                          {rule.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{rule.pattern}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span className={`px-2 py-1 rounded text-xs ${getSeverityColor(rule.severity)}`}>
                          {rule.severity}
                        </span>
                        <span>触发次数: {rule.triggered_count}</span>
                        <span>最后触发: {new Date(rule.last_triggered).toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 日志分析 */}
      {activeTab === 'log-analysis' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">分析日志数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{logAnalysisData?.total_logs_analyzed || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">唯一模式</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{logAnalysisData?.unique_patterns || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">错误模式</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{logAnalysisData?.error_patterns || 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-600">警告模式</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">{logAnalysisData?.warning_patterns || 0}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>日志模式分析</CardTitle>
            </CardHeader>
            <CardContent>
              {logAnalysisLoading ? (
                <div className="text-center text-gray-500 py-8">加载中...</div>
              ) : logAnalysisError ? (
                <div className="text-center text-red-500 py-8">加载失败</div>
              ) : (
                <div className="space-y-3">
                  {logAnalysisData?.patterns?.map((pattern, index) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <code className="text-sm bg-gray-100 px-2 py-1 rounded">{pattern.pattern}</code>
                        <span className={`px-2 py-1 rounded text-xs ${getSeverityColor(pattern.severity)}`}>
                          {pattern.severity}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>出现次数: {pattern.count}</span>
                        <span>频率: {pattern.frequency.toFixed(2)}/h</span>
                        <span>首次: {new Date(pattern.first_seen).toLocaleString()}</span>
                        <span>最近: {new Date(pattern.last_seen).toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Elasticsearch */}
      {activeTab === 'elasticsearch' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Elasticsearch 集群信息
            </CardTitle>
          </CardHeader>
          <CardContent>
            {esLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : esError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">集群名称</div>
                    <div className="font-medium">{esData?.cluster_name}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">节点数</div>
                    <div className="font-medium">{esData?.nodes_count}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">索引数</div>
                    <div className="font-medium">{esData?.total_indices}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">文档数</div>
                    <div className="font-medium">{esData?.total_documents?.toLocaleString()}</div>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium mb-2">日志查询结果</h3>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {esData?.logs?.map((log) => (
                      <div key={log._id} className="p-3 bg-gray-50 rounded text-sm">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(log._source.level)}`}>
                            {log._source.level}
                          </span>
                          <span className="text-gray-600">{log._source.service}</span>
                          <span className="text-gray-400">{new Date(log._source.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="text-gray-700">{log._source.message}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tempo */}
      {activeTab === 'tempo' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              Tempo 分布式追踪
            </CardTitle>
          </CardHeader>
          <CardContent>
            {tempoLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : tempoError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">总追踪数</div>
                    <div className="font-medium">{tempoData?.total_traces?.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">查询耗时</div>
                    <div className="font-medium">{tempoData?.search_duration_ms}ms</div>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium mb-2">追踪列表</h3>
                  <div className="space-y-2">
                    {tempoData?.traces?.map((trace) => (
                      <div key={trace.trace_id} className="p-3 bg-gray-50 rounded">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">{trace.service}</span>
                          <span className="text-sm text-gray-600">{trace.duration_ms}ms</span>
                        </div>
                        <div className="text-sm text-gray-500">
                          <span>Trace ID: {trace.trace_id}</span>
                          <span className="ml-4">Spans: {trace.span_count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Loki */}
      {activeTab === 'loki' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Loki 日志聚合
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lokiLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : lokiError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">流数量</div>
                    <div className="font-medium">{lokiData?.total_streams}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">摄入速率</div>
                    <div className="font-medium">{lokiData?.ingestion_rate_mb} MB/s</div>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium mb-2">日志流</h3>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {lokiData?.logs?.map((log, index) => (
                      <div key={index} className="p-3 bg-gray-50 rounded text-sm">
                        <div className="text-gray-600 mb-1">
                          {Object.entries(log.stream).map(([k, v]) => (
                            <span key={k} className="mr-2">
                              <span className="font-medium">{k}:</span> {v}
                            </span>
                          ))}
                        </div>
                        {log.values.map(([ts, msg], i) => (
                          <div key={i} className="text-gray-700">
                            {new Date(parseInt(ts) * 1000).toLocaleString()}: {msg}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* VictoriaMetrics */}
      {activeTab === 'victoriametrics' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              VictoriaMetrics 时序数据
            </CardTitle>
          </CardHeader>
          <CardContent>
            {vmLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : vmError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">总序列数</div>
                    <div className="font-medium">{vmData?.total_series?.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">数据大小</div>
                    <div className="font-medium">{vmData?.data_size_gb} GB</div>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium mb-2">指标数据</h3>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {vmData?.metrics?.map((metric, index) => (
                      <div key={index} className="p-3 bg-gray-50 rounded text-sm">
                        <div className="text-gray-600 mb-1">
                          {Object.entries(metric.metric).map(([k, v]) => (
                            <span key={k} className="mr-2">
                              <span className="font-medium">{k}:</span> {v}
                            </span>
                          ))}
                        </div>
                        {metric.values.map(([ts, val], i) => (
                          <div key={i} className="text-gray-700">
                            {new Date(parseInt(ts) * 1000).toLocaleString()}: {val}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
