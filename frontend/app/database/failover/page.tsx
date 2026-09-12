'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, ShieldAlert, ShieldCheck, Server, Zap, History } from 'lucide-react'

interface HealthEntry {
  status: string
  last_check: string | null
  latency_ms: number | null
}

interface FailoverStatus {
  failover_enabled: boolean
  current_primary: string
  replica_count: number
  healthy_replicas: string[]
  health_status: Record<string, HealthEntry>
  ready: boolean
}

interface FailoverEvent {
  timestamp: string
  success: boolean
  previous_primary: string
  new_primary: string
  replica_index?: number
  healthy_replicas?: string[]
}

export default function FailoverPage() {
  const queryClient = useQueryClient()
  const [promoteIndex, setPromoteIndex] = useState(0)

  const statusQuery = useQuery<FailoverStatus>({
    queryKey: ['db-failover-status'],
    queryFn: async () => (await api.get('/api/v1/database/failover/status')).data,
  })
  const status = statusQuery.data

  const historyQuery = useQuery<{ count: number; events: FailoverEvent[] }>({
    queryKey: ['db-failover-history'],
    queryFn: async () => (await api.get('/api/v1/database/failover/history')).data,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['db-failover-status'] })
    queryClient.invalidateQueries({ queryKey: ['db-failover-history'] })
  }

  const executeMutation = useMutation({
    mutationFn: async () => {
      if (!window.confirm('确认对当前主库执行故障转移？该操作会切换当前主库。')) throw new Error('已取消')
      return (await api.post('/api/v1/database/failover/execute', {})).data
    },
    onSuccess: (data) => {
      toast.success(`故障转移到 ${data.new_primary}`)
      invalidate()
    },
    onError: (err: any) => {
      if (err?.message === '已取消') return
      const detail = err?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : detail?.message || '故障转移失败')
      invalidate()
    },
  })

  const promoteMutation = useMutation({
    mutationFn: async () => (await api.post('/api/v1/database/failover/promote', { replica_index: Number(promoteIndex) })).data,
    onSuccess: (data) => {
      toast.success(`已提升副本到主库：${data.new_primary}`)
      invalidate()
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : detail?.message || '提升失败')
      invalidate()
    },
  })

  const events = historyQuery.data?.events ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">故障转移</h1>
        <Button variant="outline" onClick={() => { statusQuery.refetch(); historyQuery.refetch() }}>
          <RefreshCw className={`h-4 w-4 mr-2 ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="就绪状态" value={status?.ready ? '可转移' : '未就绪'} icon={status?.ready ? ShieldCheck : ShieldAlert}
          level={status?.ready ? 'normal' : 'warning'} />
        <KpiCard title="当前主库" value={status?.current_primary ?? '-'} icon={Server} />
        <KpiCard title="健康副本" value={status?.healthy_replicas?.length ?? 0} icon={Zap} />
        <KpiCard title="副本总数" value={status?.replica_count ?? 0} icon={Server} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>执行故障转移</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-500">
              故障转移仅在启用自动故障转移且存在健康副本时执行；系统会先刷新真实健康检查再决策。
            </p>
            <div className="flex gap-2">
              <Button disabled={!status?.failover_enabled || executeMutation.isPending} onClick={() => executeMutation.mutate()}>
                <ShieldAlert className="h-4 w-4 mr-1" /> 执行故障转移
              </Button>
            </div>
            {!status?.failover_enabled && <p className="text-xs text-amber-600">自动故障转移未启用（请在“数据库复制”页开启）。</p>}

            <div className="border-t pt-4 space-y-3">
              <Label>手动提升指定副本</Label>
              <div className="flex gap-2">
                <Input type="number" min={0} value={promoteIndex} onChange={(e) => setPromoteIndex(Number(e.target.value))} />
                <Button variant="outline" disabled={promoteMutation.isPending} onClick={() => promoteMutation.mutate()}>
                  提升为
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>节点健康</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(status?.health_status ?? {}).length ? (
              <div className="space-y-2">
                {Object.entries(status!.health_status).map(([node, h]) => (
                  <div key={node} className="flex items-center justify-between border-b pb-1 text-sm">
                    <span>{node}{node === status?.current_primary ? ' (主)' : ''}</span>
                    <Badge variant={h.status === 'healthy' ? 'default' : h.status === 'unknown' ? 'secondary' : 'destructive'}>{h.status}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">尚未配置复制拓扑。</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><History className="h-4 w-4" /> 故障转移历史</CardTitle>
        </CardHeader>
        <CardContent>
          {events.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2">时间</th>
                    <th className="py-2">结果</th>
                    <th className="py-2">原主库</th>
                    <th className="py-2">新主库</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e, i) => (
                    <tr key={i} className="border-b">
                      <td className="py-2">{new Date(e.timestamp).toLocaleString()}</td>
                      <td className="py-2"><Badge variant={e.success ? 'default' : 'destructive'}>{e.success ? '成功' : '失败'}</Badge></td>
                      <td className="py-2">{e.previous_primary}</td>
                      <td className="py-2">{e.new_primary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">暂无故障转移记录（仅记录真实执行的事件）。</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
