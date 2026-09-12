'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import { RefreshCw, Layers, CheckCircle2, PlugZap, Boxes } from 'lucide-react'

interface SystemSummary {
  total_plugins_registered: number
  total_plugins_enabled: number
  total_interfaces_defined: number
  system_version: string
  plugins_by_type: Record<string, number>
  plugins_by_status: Record<string, number>
}

interface SystemStatusResponse {
  status: string
  data: SystemSummary
  timestamp: string
}

interface PluginStats {
  total_plugins: number
  active_plugins: number
  inactive_plugins: number
  error_plugins: number
  total_executions: number
  successful_executions: number
  failed_executions: number
}

function BarRow({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-700">{label}</span>
        <span className="font-medium">{value}</span>
      </div>
      <div className="h-2 w-full rounded bg-gray-100">
        <div className="h-2 rounded bg-blue-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function PluginStatusPage() {
  const statusQuery = useQuery<SystemStatusResponse>({
    queryKey: ['plugin-system-status'],
    queryFn: async () => (await api.get('/api/plugin-system/status')).data,
  })

  const statsQuery = useQuery<PluginStats>({
    queryKey: ['plugin-stats'],
    queryFn: async () => (await api.get('/api/plugins/stats')).data,
  })

  const summary = statusQuery.data?.data
  const stats = statsQuery.data
  const byType = summary?.plugins_by_type ?? {}
  const byStatus = summary?.plugins_by_status ?? {}
  const typeMax = Math.max(1, ...Object.values(byType))
  const statusMax = Math.max(1, ...Object.values(byStatus))
  const execTotal = stats?.total_executions ?? 0
  const successRate =
    execTotal > 0 ? Math.round(((stats?.successful_executions ?? 0) / execTotal) * 100) : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">插件系统状态</h1>
        <Button variant="outline" onClick={() => { statusQuery.refetch(); statsQuery.refetch() }}>
          <RefreshCw className={`h-4 w-4 mr-2 ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {statusQuery.isError && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-red-700">无法获取插件系统状态</div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="已注册插件" value={summary?.total_plugins_registered ?? 0} icon={Boxes} />
        <KpiCard title="已启用插件" value={summary?.total_plugins_enabled ?? 0} icon={CheckCircle2} />
        <KpiCard title="接口定义" value={summary?.total_interfaces_defined ?? 0} icon={PlugZap} />
        <KpiCard title="系统版本" value={summary?.system_version ?? '-'} icon={Layers} />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>按类型分布</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.keys(byType).length === 0 ? (
              <p className="text-sm text-gray-500">暂无数据</p>
            ) : (
              Object.entries(byType).map(([k, v]) => <BarRow key={k} label={k} value={v} max={typeMax} />)
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>按状态分布</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.keys(byStatus).length === 0 ? (
              <p className="text-sm text-gray-500">暂无数据</p>
            ) : (
              Object.entries(byStatus).map(([k, v]) => <BarRow key={k} label={k} value={v} max={statusMax} />)
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>执行统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <div className="text-sm text-gray-500">总执行</div>
              <div className="text-2xl font-semibold">{execTotal}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">成功</div>
              <div className="text-2xl font-semibold text-green-600">{stats?.successful_executions ?? 0}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">失败</div>
              <div className="text-2xl font-semibold text-red-600">{stats?.failed_executions ?? 0}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">成功率</div>
              <Badge variant={successRate >= 90 ? 'default' : 'destructive'}>{successRate}%</Badge>
            </div>
          </div>
          <p className="mt-3 text-xs text-gray-500">
            最后更新: {statusQuery.data?.timestamp ? new Date(statusQuery.data.timestamp).toLocaleString() : '-'}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
