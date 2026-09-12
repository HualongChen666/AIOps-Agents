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
import { RefreshCw, Database, Copy, Split, ShieldCheck, HeartPulse, Plus, Trash2 } from 'lucide-react'

interface HealthEntry {
  status: string
  last_check: string | null
  latency_ms: number | null
  error?: string
}

interface ReplicationStatus {
  enabled: boolean
  read_write_splitting: boolean
  failover_enabled: boolean
  current_primary: string
  replica_count: number
  health_status: Record<string, HealthEntry>
}

interface ReplicaRow {
  host: string
  port: number
}

export default function ReplicationPage() {
  const queryClient = useQueryClient()
  const [primary, setPrimary] = useState({ host: '127.0.0.1', port: 5432 })
  const [replicas, setReplicas] = useState<ReplicaRow[]>([{ host: '127.0.0.1', port: 5433 }])
  const [readWriteSplitting, setReadWriteSplitting] = useState(true)
  const [failoverEnabled, setFailoverEnabled] = useState(false)

  const statusQuery = useQuery<ReplicationStatus>({
    queryKey: ['db-replication-status'],
    queryFn: async () => (await api.get('/api/v1/database/replication/status')).data,
  })
  const status = statusQuery.data

  const configureMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/v1/database/replication/configure', {
        primary: { host: primary.host.trim(), port: Number(primary.port) },
        replicas: replicas
          .filter((r) => r.host.trim())
          .map((r) => ({ host: r.host.trim(), port: Number(r.port) })),
        read_write_splitting: readWriteSplitting,
        failover_enabled: failoverEnabled,
      })
      return res.data as ReplicationStatus
    },
    onSuccess: (data) => {
      toast.success(`已配置复制：${data.replica_count} 个副本`)
      queryClient.invalidateQueries({ queryKey: ['db-replication-status'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || '配置失败'),
  })

  const healthMutation = useMutation({
    mutationFn: async () => (await api.get('/api/v1/database/replication/health')).data,
    onSuccess: () => {
      toast.success('健康检查完成')
      queryClient.invalidateQueries({ queryKey: ['db-replication-status'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || '健康检查失败'),
  })

  const healthEntries = Object.entries(status?.health_status ?? {})

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据库复制</h1>
        <div className="flex gap-2">
          <Button variant="outline" disabled={!status?.enabled || healthMutation.isPending} onClick={() => healthMutation.mutate()}>
            <HeartPulse className="h-4 w-4 mr-2" /> 健康检查
          </Button>
          <Button variant="outline" onClick={() => statusQuery.refetch()}>
            <RefreshCw className={`h-4 w-4 mr-2 ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="复制状态" value={status?.enabled ? '已启用' : '未配置'} icon={Copy}
          level={status?.enabled ? 'normal' : 'warning'} />
        <KpiCard title="副本数" value={status?.replica_count ?? 0} icon={Database} />
        <KpiCard title="读写分离" value={status?.read_write_splitting ? '开启' : '关闭'} icon={Split} />
        <KpiCard title="自动故障转移" value={status?.failover_enabled ? '开启' : '关闭'} icon={ShieldCheck} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>配置复制拓扑</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>主库地址</Label>
                <Input value={primary.host} onChange={(e) => setPrimary({ ...primary, host: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>主库端口</Label>
                <Input type="number" value={primary.port} onChange={(e) => setPrimary({ ...primary, port: Number(e.target.value) })} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>副本</Label>
                <Button variant="outline" size="sm" onClick={() => setReplicas([...replicas, { host: '', port: 5433 }])}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {replicas.map((r, i) => (
                <div key={i} className="flex gap-2">
                  <Input placeholder="host" value={r.host} onChange={(e) => setReplicas(replicas.map((x, j) => (j === i ? { ...x, host: e.target.value } : x)))} />
                  <Input type="number" className="w-28" value={r.port} onChange={(e) => setReplicas(replicas.map((x, j) => (j === i ? { ...x, port: Number(e.target.value) } : x)))} />
                  <Button variant="outline" size="sm" onClick={() => setReplicas(replicas.filter((_, j) => j !== i))}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>

            <div className="flex gap-6 text-sm">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={readWriteSplitting} onChange={(e) => setReadWriteSplitting(e.target.checked)} />
                启用读写分离
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={failoverEnabled} onChange={(e) => setFailoverEnabled(e.target.checked)} />
                启用自动故障转移
              </label>
            </div>

            <Button disabled={configureMutation.isPending} onClick={() => configureMutation.mutate()}>应用配置</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>复制健康状态</CardTitle>
          </CardHeader>
          <CardContent>
            {healthEntries.length ? (
              <div className="space-y-2">
                <div className="text-sm text-gray-600">当前主库：<Badge>{status?.current_primary}</Badge></div>
                {healthEntries.map(([node, h]) => (
                  <div key={node} className="flex items-center justify-between border-b pb-1 text-sm">
                    <span>{node}</span>
                    <span className="flex items-center gap-2">
                      {h.latency_ms != null && <span className="text-gray-400">{h.latency_ms.toFixed(1)}ms</span>}
                      <Badge variant={h.status === 'healthy' ? 'default' : h.status === 'unknown' ? 'secondary' : 'destructive'}>
                        {h.status}
                      </Badge>
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">尚未配置复制。配置后点击“健康检查”执行真实 TCP 探测。</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
