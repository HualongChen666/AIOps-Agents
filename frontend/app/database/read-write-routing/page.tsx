'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { KpiCard } from '@/components/ui/KpiCard'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { RefreshCw, GitBranch, Server, Activity, Split, Play, Plus, Trash2 } from 'lucide-react'

interface ReplicaStat {
  host: string
  port: number
  state: string
  lag: number
  connections: number
  load_score: number
}

interface RouterStats {
  total_queries: number
  read_write_splitting_enabled: boolean
  replicas_count: number
  healthy_replicas: number
  load_balancing_method: string
  replicas: Record<string, ReplicaStat>
}

interface RouteDecision {
  target_host: string
  target_port: number
  query_type: string
  replica_used: boolean
  routing_reason: string
}

interface ReplicaRow {
  host: string
  port: number
}

const METHODS = [
  { value: 'round_robin', label: '轮询 (round_robin)' },
  { value: 'least_lag', label: '最小延迟 (least_lag)' },
  { value: 'least_connections', label: '最少连接 (least_connections)' },
]

export default function ReadWriteRoutingPage() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ primary_host: '127.0.0.1', primary_port: 5432, load_balancing_method: 'round_robin', lag_threshold: 5 })
  const [replicas, setReplicas] = useState<ReplicaRow[]>([{ host: '127.0.0.1', port: 5433 }])
  const [query, setQuery] = useState('SELECT * FROM orders WHERE id = 1')
  const [decision, setDecision] = useState<RouteDecision | null>(null)

  const statsQuery = useQuery<RouterStats>({
    queryKey: ['db-rw-stats'],
    queryFn: async () => (await api.get('/api/v1/database/read-write-routing/stats')).data,
  })
  const stats = statsQuery.data

  const configureMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/v1/database/read-write-routing/configure', {
        primary_host: form.primary_host.trim(),
        primary_port: Number(form.primary_port),
        replicas: replicas.filter((r) => r.host.trim()).map((r) => ({ host: r.host.trim(), port: Number(r.port) })),
        load_balancing_method: form.load_balancing_method,
        lag_threshold: Number(form.lag_threshold),
      })
      return res.data as RouterStats
    },
    onSuccess: () => {
      toast.success('读写路由器已配置')
      queryClient.invalidateQueries({ queryKey: ['db-rw-stats'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || '配置失败'),
  })

  const routeMutation = useMutation({
    mutationFn: async () => (await api.post('/api/v1/database/read-write-routing/route', { query })).data as RouteDecision,
    onSuccess: (data) => {
      setDecision(data)
      queryClient.invalidateQueries({ queryKey: ['db-rw-stats'] })
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || '路由失败'),
  })

  const splittingMutation = useMutation({
    mutationFn: async (enabled: boolean) => (await api.post('/api/v1/database/read-write-routing/splitting', { enabled })).data,
    onSuccess: (data: RouterStats) => {
      toast.success(`读写分离已${data.read_write_splitting_enabled ? '开启' : '关闭'}`)
      queryClient.invalidateQueries({ queryKey: ['db-rw-stats'] })
    },
  })

  const replicaStats = Object.entries(stats?.replicas ?? {})

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">读写分离</h1>
        <Button variant="outline" onClick={() => statsQuery.refetch()}>
          <RefreshCw className={`h-4 w-4 mr-2 ${statsQuery.isFetching ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard title="已路由查询" value={stats?.total_queries ?? 0} icon={GitBranch} />
        <KpiCard title="副本数" value={stats?.replicas_count ?? 0} icon={Server} />
        <KpiCard title="健康副本" value={stats?.healthy_replicas ?? 0} icon={Activity} />
        <KpiCard title="负载策略" value={stats?.load_balancing_method ?? '-'} icon={Split} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>路由器配置</CardTitle>
              <Badge variant={stats?.read_write_splitting_enabled ? 'default' : 'secondary'}>
                读写分离 {stats?.read_write_splitting_enabled ? '开' : '关'}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>主库地址</Label>
                <Input value={form.primary_host} onChange={(e) => setForm({ ...form, primary_host: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>主库端口</Label>
                <Input type="number" value={form.primary_port} onChange={(e) => setForm({ ...form, primary_port: Number(e.target.value) })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>负载均衡策略</Label>
                <Select value={form.load_balancing_method} onChange={(e) => setForm({ ...form, load_balancing_method: e.target.value })}>
                  {METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </Select>
              </div>
              <div className="space-y-1">
                <Label>复制延迟阈值(秒)</Label>
                <Input type="number" value={form.lag_threshold} onChange={(e) => setForm({ ...form, lag_threshold: Number(e.target.value) })} />
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

            <div className="flex flex-wrap gap-2">
              <Button disabled={configureMutation.isPending} onClick={() => configureMutation.mutate()}>保存配置</Button>
              <Button variant="outline" onClick={() => splittingMutation.mutate(!stats?.read_write_splitting_enabled)}>
                {stats?.read_write_splitting_enabled ? '关闭' : '开启'}读写分离
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>查询路由测试</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label>SQL 语句</Label>
              <textarea
                className="w-full rounded-md border border-gray-300 p-2 text-sm font-mono"
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <Button variant="outline" disabled={routeMutation.isPending} onClick={() => routeMutation.mutate()}>
              <Play className="h-4 w-4 mr-1" /> 计算路由
            </Button>
            {decision && (
              <div className="rounded border p-3 text-sm space-y-1">
                <div>类型 <Badge>{decision.query_type}</Badge>
                  <Badge className="ml-2" variant={decision.replica_used ? 'default' : 'secondary'}>
                    {decision.replica_used ? '副本' : '主库'}
                  </Badge>
                </div>
                <div className="text-gray-600">目标 {decision.target_host}:{decision.target_port}</div>
                <div className="text-gray-500">{decision.routing_reason}</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>副本状态</CardTitle>
        </CardHeader>
        <CardContent>
          {replicaStats.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2">副本</th>
                    <th className="py-2">状态</th>
                    <th className="py-2">延迟(s)</th>
                    <th className="py-2">连接数</th>
                    <th className="py-2">负载分</th>
                  </tr>
                </thead>
                <tbody>
                  {replicaStats.map(([rid, r]) => (
                    <tr key={rid} className="border-b">
                      <td className="py-2 font-medium">{rid} <span className="text-gray-400">({r.host}:{r.port})</span></td>
                      <td className="py-2"><Badge variant={r.state === 'healthy' ? 'default' : 'destructive'}>{r.state}</Badge></td>
                      <td className="py-2">{r.lag}</td>
                      <td className="py-2">{r.connections}</td>
                      <td className="py-2">{r.load_score.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">尚未配置副本。保存配置后此处会显示真实副本状态。</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
