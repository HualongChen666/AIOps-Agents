'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import api from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, BarChart3, TrendingUp, AlertTriangle, Activity, GitCompare } from 'lucide-react'

interface ChartDataPoint {
  timestamp: string
  value: number
}

interface ChartSeries {
  name: string
  data: ChartDataPoint[]
  unit?: string
  color?: string
}

interface ChartResponse {
  title: string
  series: ChartSeries[]
  time_range: {
    start: string
    end: string
    preset: string
  }
  metadata?: Record<string, any>
}

interface AlertData {
  name: string
  value: number
  color: string
}

interface AlertResponse {
  title: string
  data: AlertData[]
  time_range: {
    start: string
    end: string
    preset: string
  }
  metadata?: Record<string, any>
}

export default function ChartAggregationPage() {
  const [selectedMetrics, setSelectedMetrics] = useState('cpu_usage,memory_usage')
  const [timeRange, setTimeRange] = useState('24h')
  const [groupBy, setGroupBy] = useState('severity')
  const [metricName, setMetricName] = useState('cpu_usage')
  const [entities, setEntities] = useState('Service A,Service B')
  const [activeTab, setActiveTab] = useState('metrics')

  // 获取聚合指标数据
  const { data: metricsData, isLoading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useQuery({
    queryKey: ['chart-metrics', selectedMetrics, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/charts/metrics', {
        params: {
          metric_names: selectedMetrics,
          time_range: timeRange,
          interval: '1h',
          aggregation: 'avg'
        }
      })
      return resp.data as ChartResponse
    },
    refetchInterval: 60000
  })

  // 获取聚合告警数据
  const { data: alertsData, isLoading: alertsLoading, error: alertsError, refetch: refetchAlerts } = useQuery({
    queryKey: ['chart-alerts', groupBy, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/charts/alerts', {
        params: {
          group_by: groupBy,
          time_range: timeRange
        }
      })
      return resp.data as AlertResponse
    },
    refetchInterval: 60000
  })

  // 获取聚合性能数据
  const { data: performanceData, isLoading: performanceLoading, error: performanceError, refetch: refetchPerformance } = useQuery({
    queryKey: ['chart-performance', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/charts/performance', {
        params: {
          time_range: timeRange,
          interval: '1h'
        }
      })
      return resp.data as ChartResponse
    },
    refetchInterval: 60000
  })

  // 获取趋势分析数据
  const { data: trendsData, isLoading: trendsLoading, error: trendsError, refetch: refetchTrends } = useQuery({
    queryKey: ['chart-trends', metricName, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/charts/trends', {
        params: {
          metric_name: metricName,
          time_range: timeRange,
          prediction_hours: 24
        }
      })
      return resp.data
    },
    refetchInterval: 120000
  })

  // 获取对比数据
  const { data: compareData, isLoading: compareLoading, error: compareError, refetch: refetchCompare } = useQuery({
    queryKey: ['chart-compare', metricName, entities, timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/charts/compare', {
        params: {
          metric_name: metricName,
          entities: entities,
          time_range: timeRange
        }
      })
      return resp.data as ChartResponse
    },
    refetchInterval: 120000
  })

  const handleRefreshAll = () => {
    refetchMetrics()
    refetchAlerts()
    refetchPerformance()
    refetchTrends()
    refetchCompare()
  }

  const renderLineChart = (series: ChartSeries[], height = 200) => {
    if (!series || series.length === 0) return <div className="text-center text-gray-500 py-8">暂无数据</div>

    const allValues = series.flatMap(s => s.data.map(d => d.value))
    const min = Math.min(...allValues)
    const max = Math.max(...allValues)
    const range = max - min || 1

    const width = 600
    const pad = 30

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full" preserveAspectRatio="none">
        <rect x="0" y="0" width={width} height={height} fill="#ffffff" />
        {Array.from({ length: 5 }).map((_, i) => {
          const y = pad + (height - 2 * pad) * (i / 4)
          return (
            <line key={`grid-${i}`} x1={pad} y1={y} x2={width - pad} y2={y} stroke="#e5e7eb" strokeWidth={1} />
          )
        })}
        {series.map((s, seriesIndex) => {
          const points = s.data.map((d, i) => {
            const x = pad + (width - 2 * pad) * (i / Math.max(1, s.data.length - 1))
            const y = height - pad - ((d.value - min) / range) * (height - 2 * pad)
            return `${x},${y}`
          })
          const linePath = `M ${points.join(' L ')}`
          return (
            <path
              key={`series-${seriesIndex}`}
              d={linePath}
              fill="none"
              stroke={s.color || '#3b82f6'}
              strokeWidth={2}
            />
          )
        })}
      </svg>
    )
  }

  const renderBarChart = (data: AlertData[], height = 200) => {
    if (!data || data.length === 0) return <div className="text-center text-gray-500 py-8">暂无数据</div>

    const maxValue = Math.max(...data.map(d => d.value))
    const width = 600
    const pad = 30
    const barWidth = (width - 2 * pad) / data.length

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full" preserveAspectRatio="none">
        <rect x="0" y="0" width={width} height={height} fill="#ffffff" />
        {data.map((d, i) => {
          const h = (d.value / maxValue) * (height - 2 * pad)
          const x = pad + i * barWidth
          const y = height - pad - h
          return (
            <g key={`bar-${i}`}>
              <rect x={x + 1} y={y} width={Math.max(1, barWidth - 2)} height={h} fill={d.color} />
              <text x={x + barWidth / 2} y={height - 10} textAnchor="middle" fontSize="10" fill="#6b7280">
                {d.name}
              </text>
              <text x={x + barWidth / 2} y={y - 5} textAnchor="middle" fontSize="10" fill="#374151">
                {d.value}
              </text>
            </g>
          )
        })}
      </svg>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">图表聚合</h1>
          <p className="text-sm text-gray-500 mt-1">多维度数据聚合与可视化分析</p>
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
          { id: 'metrics', label: '指标聚合', icon: BarChart3 },
          { id: 'alerts', label: '告警聚合', icon: AlertTriangle },
          { id: 'performance', label: '性能聚合', icon: Activity },
          { id: 'trends', label: '趋势分析', icon: TrendingUp },
          { id: 'compare', label: '对比分析', icon: GitCompare }
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
                <option value="1h">1小时</option>
                <option value="6h">6小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
                <option value="30d">30天</option>
              </Select>
            </div>
            {activeTab === 'metrics' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">指标选择</label>
                <Select
                  value={selectedMetrics}
                  onChange={(e) => setSelectedMetrics(e.target.value)}
                  className="w-full"
                >
                  <option value="cpu_usage,memory_usage">CPU + 内存</option>
                  <option value="cpu_usage,memory_usage,disk_usage">CPU + 内存 + 磁盘</option>
                  <option value="network_in,network_out">网络流量</option>
                  <option value="request_count,error_rate">请求 + 错误率</option>
                  <option value="response_time">响应时间</option>
                </Select>
              </div>
            )}
            {activeTab === 'alerts' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">分组方式</label>
                <Select
                  value={groupBy}
                  onChange={(e) => setGroupBy(e.target.value)}
                  className="w-full"
                >
                  <option value="severity">按级别</option>
                  <option value="category">按类别</option>
                  <option value="source">按来源</option>
                </Select>
              </div>
            )}
            {activeTab === 'trends' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">指标名称</label>
                <Select
                  value={metricName}
                  onChange={(e) => setMetricName(e.target.value)}
                  className="w-full"
                >
                  <option value="cpu_usage">CPU使用率</option>
                  <option value="memory_usage">内存使用率</option>
                  <option value="disk_usage">磁盘使用率</option>
                  <option value="error_rate">错误率</option>
                  <option value="response_time">响应时间</option>
                </Select>
              </div>
            )}
            {activeTab === 'compare' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">对比实体</label>
                <Select
                  value={entities}
                  onChange={(e) => setEntities(e.target.value)}
                  className="w-full"
                >
                  <option value="Service A,Service B">服务A vs 服务B</option>
                  <option value="Production,Staging">生产 vs 预发布</option>
                  <option value="Region A,Region B,Region C">多区域对比</option>
                </Select>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 指标聚合图表 */}
      {activeTab === 'metrics' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              指标聚合
            </CardTitle>
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : metricsError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-6">
                {metricsData?.series?.map((series, index) => (
                  <div key={index}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">{series.name}</span>
                      <span className="text-sm text-gray-600">
                        单位: {series.unit || ''}
                      </span>
                    </div>
                    <div className="h-64">
                      {renderLineChart([series])}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 告警聚合图表 */}
      {activeTab === 'alerts' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              告警聚合
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alertsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : alertsError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="h-64">
                {renderBarChart(alertsData?.data || [])}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 性能聚合图表 */}
      {activeTab === 'performance' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              性能聚合
            </CardTitle>
          </CardHeader>
          <CardContent>
            {performanceLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : performanceError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-6">
                {performanceData?.series?.map((series, index) => (
                  <div key={index}>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">{series.name}</span>
                      <span className="text-sm text-gray-600">
                        单位: {series.unit || ''}
                      </span>
                    </div>
                    <div className="h-64">
                      {renderLineChart([series])}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 趋势分析图表 */}
      {activeTab === 'trends' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              趋势分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            {trendsLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : trendsError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">历史数据</h3>
                  <div className="h-64">
                    {renderLineChart([{ name: '历史', data: trendsData?.historical || [], color: '#3b82f6' }])}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">预测数据</h3>
                  <div className="h-64">
                    {renderLineChart([{ name: '预测', data: trendsData?.prediction || [], color: '#10b981' }])}
                  </div>
                </div>
                {trendsData?.anomalies && trendsData.anomalies.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">异常点</h3>
                    <div className="space-y-2">
                      {trendsData.anomalies.map((anomaly: any, index: number) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-red-50 rounded">
                          <span className="text-sm">{anomaly.timestamp}</span>
                          <span className="text-sm font-medium text-red-600">
                            {anomaly.type === 'high' ? '过高' : '过低'}: {anomaly.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 对比分析图表 */}
      {activeTab === 'compare' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              对比分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            {compareLoading ? (
              <div className="text-center text-gray-500 py-8">加载中...</div>
            ) : compareError ? (
              <div className="text-center text-red-500 py-8">加载失败</div>
            ) : (
              <div className="h-64">
                {renderLineChart(compareData?.series || [])}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
